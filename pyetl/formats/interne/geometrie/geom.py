# -*- coding: utf-8 -*-
''' definition interne des objets
attributs et geometrie '''

import itertools
from . import composants as C



class Geometrie(object):
    '''classe de base de stockage de la geometrie d'un objet'''
    def __init__(self):
        self.polygones = []
        self.lignes = []
        self.point = None
        self.type = 'indef' # type de geometrie
        self.null = True #geometrie nulle
        self.valide = False
        self.courbe = False
        self.dimension = 0
        self.multi = 0
        self.npnt = 0
        self.srid = '3948'
        self.force_multi=False
        #self.epsg = 'SRID=3948;'
        self.erreurs = Erreurs()


    @property
    def epsg(self):
        ''' retourne la projection sous forme d'une chaine SRID'''
        return 'SRID='+self.srid+';'

    def setsrid(self,srid):
        '''positionne le code EPSG'''
        if srid:
            self.srid = str(int(srid))

    @property
    def npt(self):
        ''' retourne le nombre de points en eliminant les points doubles entre sections'''
        if self.type < '2':
            return len(self.composants)
        cc=self.composants
        return sum([i.npt for i in cc])-sum([len(i.sections)- (0 if i.ferme else 1)  for i in cc])

    @property
    def ferme(self):
        ''' retourne True si la geometrie est fermee'''
        for i in self.lignes:
            if not i.ferme:
                return False
        return True

    @property
    def composants(self):
        ''' retourne les elements de la geometrie'''
        if self.type=='1':
            return [self.point]
#        if self.type=='0':
#            return []
        return self.lignes


    @property
    def __json_if__(self):
        '''  interface de type json '''
#        print ('jsonio ',self.type, self.null)
        if self.type == '0':
            return None
        dim=self.dimension
        if self.null: # geometrie non definie
            return '"geometry": null\n'
        if self.type == '1': # point
            return '"geometry": {\n"type": "Point",\n"coordinates":['+\
                    ','.join(map(str,self.point.coords[0][:dim]))+']\n}'

        if self.type == '2':
#            print ('type 2')
            if len(self.lignes) == 1 :
                return '"geometry": {\n"type": "LineString",\n"coordinates":[\n['+\
                        '],\n[' .join([','.join(map(str,i[:dim])) for i in self.lignes[0].coords])+']\n]\n}'
            else:
                return '"geometry": {\n"type": "MultiLineString",\n"coordinates":[\n[\n['+\
                        ']],\n[[' .join(['],\n['.join([','.join(map(str,i[:dim])) for i in j.coords])
                                        for j in self.lignes] )+']\n]\n]\n}'
        if self.type == '3':
            if len(self.polygones) == 1:
                if len(self.lignes) == 1: # polygone sans trous
                    return '"geometry": {\n"type": "Polygon",\n"coordinates":[\n[\n['+\
                        '],\n[' .join([','.join(map(str,i[:dim])) for i in self.lignes[0].coords])+']\n]\n]\n}'
                else:
                    return '"geometry": {\n"type": "Polygon",\n"coordinates":[\n[\n['+\
                        ']],\n[[' .join(['],\n['.join([','.join(map(str,i[:dim])) for i in j.coords])
                                        for j in self.lignes] )+']\n]\n]\n}'


            return '"geometry": {\n"type": "MultiPolygon",\n"coordinates":[\n[\n[\n['+\
                        ']]],\n[[[' .join([']],\n[['.join(['],\n['.join([','.join(map(str,pnt[:dim])) for pnt in lin.coords])
                                                        for lin in pol.lignes])
                                        for pol in self.polygones])+']\n]\n]\n]\n}'
        if self.type == '4': #tin
            return '"geometry": {\n"type": "Tin",\n"coordinates":[\n[\n[\n['+\
                        ']]],\n[[[' .join([']],\n[['.join(['],\n['.join([','.join(map(str,pnt[:dim])) for pnt in lin.coords])
                                                        for lin in pol.lignes])
                                        for pol in self.polygones])+']\n]\n]\n]\n}'


        if self.type == '5': #polyhedralsurface
            return '"geometry": {\n"type": "PolyhedralSurface",\n"coordinates":[\n[\n[\n['+\
                        ']]],\n[[[' .join([']],\n[['.join(['],\n['.join([','.join(map(str,pnt[:dim])) for pnt in lin.coords])
                                                        for lin in pol.lignes])
                                        for pol in self.polygones])+']\n]\n]\n]\n}'



    @property
    def __geo_interface__(self):
        if self.type == '0':
            return {}
        dim = self.dimension
        if self.type == '1': # point
            return {
            'type': 'Point',
            'coordinates': tuple(self.point.coords[0][:dim])
            }

        elif self.type == '2':
            multi=self.force_multi or self.multi or len(self.lignes)>1
            if multi:
                coordinates = []
                for ligne in self.lignes:
                    coordinates.append(tuple([tuple(p[:dim]) for p in ligne.coords]))
                return {
                'type': 'MultiLineString',
                'coordinates': tuple(coordinates)
                }

            else:
                return {
                'type': 'LineString',
                'coordinates': tuple([tuple(p[:dim]) for p in self.lignes[0].sections[0].coords])
                }

        elif self.type == '3':
            multi=self.force_multi or self.multi or len(self.polygones)>1

            if multi:
                polys=[]
                for poly in self.polygones:
                    rings=[]
#                    print ('geoif mpol',len(poly.lignes), len(self.polygones) )

                    for ligne in poly.lignes:
                        rings.append(tuple([tuple(p[:dim]) for p in ligne.coords]))
                    polys.append(tuple(rings))
                return {
                        'type': 'MultiPolygon',
                        'coordinates': tuple(polys)
                        }
            else:
                rings=[]
#                print ('geoif pol',len(self.polygones[0].lignes))
                for ligne in self.polygones[0].lignes:
                    rings.append(tuple([tuple(p[:dim]) for p in ligne.coords]))
                return {
                        'type': 'Polygon',
                        'coordinates': tuple(rings)
                        }

        elif self.type == '4': #tin
            for poly in self.polygones:
                rings=[]
                for ligne in poly.lignes:
                    rings.append(tuple([tuple(p[:dim]) for p in ligne.coords]))
                polys.append(tuple(rings))
            return {
                    'type': 'Tin',
                    'coordinates': tuple(polys)
                    }

        elif self.type == '5': #tin
            for poly in self.polygones:
                rings=[]
                for ligne in poly.lignes:
                    rings.append(tuple([tuple(p[:dim]) for p in ligne.coords]))
                polys.append(tuple(rings))
            return {
                    'type': 'PolyhedralSurface',
                    'coordinates': tuple(polys)
                    }








    def from_geo_interface(self,geo_if): # cree une geometrie a partir de la geo_interface
#        print ('geom from geo_if',geo_if)
        if not geo_if:
            self.finalise_geom(typegeom='0')
            return
        if geo_if["type"] == 'Point':
            self.setpoint(geo_if['coordinates'],0,len(geo_if['coordinates']))
            self.finalise_geom(typegeom='1')

        elif geo_if["type"] == 'LineString':
            dim = len(geo_if["coordinates"][0])
            self.cree_section(geo_if["coordinates"],dim,1,0)

#            self.nouvelle_ligne_s(C.Section(list(geo_if["coordinates"]),dim))
#            for pt in geo_if["coordinates"]:
#                self.addpoint(pt,dim)
            self.finalise_geom(typegeom='2')
        elif geo_if["type"] == 'MultiLineString':
            dim = len(geo_if["coordinates"][0][0])
            for ligne in geo_if["coordinates"]:
                self.cree_section(ligne,dim,1,0)

#                self.nouvelle_ligne_s(C.Section(list(ligne),dim))

#                for pt in ligne:
#                    self.addpoint(pt,dim)
#                self.fin_section(1,0)
            self.finalise_geom(typegeom='2')
        elif geo_if["type"] == 'Polygon':
            dim = len(geo_if["coordinates"][0][0])
#            print ('gif:polygone',geo_if["coordinates"][0][0])
            interieur = False
            for ligne in geo_if["coordinates"]:
                self.cree_section(ligne,dim,1,0, interieur=interieur)
#                print ('lin',ligne,interieur,len(self.lignes))

                interieur = True

#                self.nouvelle_ligne_s(C.Section(list(ligne),dim))


#            for pt in geo_if["coordinates"][0]:
#                self.addpoint(pt,dim)
            self.finalise_geom(typegeom='3')
            self.multi = True

#            print ('creation polygone',len(self.polygones), self.multi)
        elif geo_if["type"] == 'MultiPolygon':
            dim = len(geo_if["coordinates"][0][0][0])
            interieur = False
            for poly in geo_if["coordinates"]:
                for ligne in poly:
                    self.cree_section(ligne,dim,1,0)
                    interieur = True
#                    self.nouvelle_ligne_s(C.Section(list(ligne),dim))
#                    for pt in ligne:
#                        self.addpoint(pt,dim)
#                    self.fin_section(1,0)
            self.finalise_geom(typegeom='3')
            self.multi = True

        elif geo_if["type"] == 'Tin':
            dim = len(geo_if["coordinates"][0][0][0])
            for poly in geo_if["coordinates"]:

                for ligne in poly:
                    self.cree_section(ligne,dim,1,0)

#                    self.nouvelle_ligne_s(C.Section(list(ligne),dim))
#                    for pt in ligne:
#                        self.addpoint(pt,dim)
#                    self.fin_section(1,0)
            self.finalise_geom(typegeom='4', orientation='L')

        elif geo_if["type"] == 'PolyhedralSurface':
            dim = len(geo_if["coordinates"][0][0][0])
            for poly in geo_if["coordinates"]:

                for ligne in poly:
                    self.cree_section(ligne,dim,1,0)

#                    self.nouvelle_ligne_s(C.Section(list(ligne),dim))
#                    for pt in ligne:
#                        self.addpoint(pt,dim)
#                    self.fin_section(1,0)
            self.finalise_geom(typegeom='5', orientation='L')
        else:
            print ('geom:geometrie inconnue ',geo_if)
#        print ('geometrie',self.type,list(self.coords))



    def __repr__(self):
        if self.valide:
            return 'type:'+self.type + ' '.join(str(i) for i in self.coords)
        return 'geometrie invalide ' + self.erreurs.__repr__()



    def setpoint(self, coords, angle, dim, longueur=0, srid='3948'):
        '''cree une geometrie de point'''
        self.type = '1'
        self.null = False
        self.dimension = dim
        self.srid = str(int(srid))
        self.valide = True
        self.point = C.Point(coords, angle, dim)
        if coords is None:
            self.null = True
        if longueur:
            self.point.longueur = longueur
#        print ('creation point ',coords, self.point.coords)


    def addpoint(self, pnt, dim):
        '''ajoute un point a une geometrie'''
        if self.lignes:
            ligne_active=self.lignes[-1]
            if ligne_active.addpoint(pnt, dim):
            # la ligne est fermee
                self.nouvelle_ligne_p(pnt, dim)
                # on ajoute un point a une nouvelle ligne
        else:
            self.lignes = [C.Ligne(C.Section(pnt, dim))]
#

    def nouvelle_ligne_s(self, sect, interieur=None):
        '''finit la ligne courante et en demarre une nouvelle avec une section'''
        self.lignes.append(C.Ligne(sect,interieur=interieur))

    def nouvelle_ligne_p(self, pnt, dim=2):
        '''finit la ligne courante et en demarre une nouvelle avec un point'''
        self.lignes.append(C.Ligne(C.Section(pnt, dim)))

    def cree_section(self,liste_pts,dim,couleur,courbe,interieur=None):
        '''cree une section et l'ajoute a la geometrie courante'''
        sect = C.Section(None,dim)
        sect.setsect(liste_pts,couleur,courbe)
        self.ajout_section(sect,interieur)
        #self.print_debug()

    def ajout_section(self, sect, interieur):
        '''ajoute une section a la geometrie'''
        if self.lignes:
            if self.lignes[-1].ajout_section(sect):
#                print ('objet:creation nouvelle ligne')
                self.nouvelle_ligne_s(sect,interieur)
        else:
            self.lignes=[C.Ligne(sect,interieur=False)]

    def fin_section(self, couleur, courbe):
        ''' termine la section courante '''
        sect = self.lignes[-1].fin_section(couleur, courbe)
        if sect: # on a tente d'ajouter un cercle
            self.nouvelle_ligne_s(sect)


    def annule_section(self):
        '''annule la derniere section en cours'''
        if self.lignes[-1].annule_section():
            self.lignes.pop()

    def finalise_geom(self, typegeom='0', orientation='L'):
        '''termine une geometrie et finalise la structure'''
        self.valide = 1
        self.multi = False
        self.courbe = False


        self.null =  not self.coords
        if typegeom=='0':
            self.type='0'
            self.lignes = []
            self.polygones = []
            return True

        if self.null:
            return False
        if self.type == '1':
            #self.npt=1
            self.lignes = []
            self.polygones = []
            return True


        if typegeom != '2':
            if self.ferme:
            # toutes les lignes sont fermees et on autorise des polygones
#                print( 'finalisation', len(self.lignes))
                for i in self.lignes:
                    aire = i.aire_orientee()
                    if aire == 0:
                        self.erreurs.ajout_erreur("contour degénéré "+typegeom)
                        self.valide = False
                        return False
                    if orientation == 'R':
                        aire = -aire
                    if i.interieur is None:
                        i.interieur = aire < 0
                    if i.interieur:
                        if self.polygones:
                            self.polygones[-1].ajout_contour(i)
                        else:
                            i.interieur = False
                            self.polygones.append(C.Polygone(i))
                            self.erreurs.ajout_warning("interieur")
                    else:
                        self.polygones.append(C.Polygone(i))
        if self.lignes:
            self.type = '3' if self.polygones else '2'
#        print ('fin_geom:type_geom ', self.type, typegeom)
#        if typegeom==2:
#            raise
        if self.type == '2':
            for i in self.lignes:
                if i.npt<2:
                    self.erreurs.ajout_erreur("ligne un point")
                    self.valide = False
        self.multi = len(self.polygones)-1 if self.polygones else len(self.lignes)-1
        self.courbe = True in [bool(i.courbe) for i in self.lignes]
        if self.lignes:
            self.dimension = self.lignes[0].dimension
        if self .type=='3' and (typegeom == '4' or typegeom=='5'):
            self.type=typegeom

        elif typegeom != '-1' and typegeom != 'indef' and typegeom != self.type:
            self.erreurs.ajout_warning("attention geometrie demandee: "+ typegeom +' trouve '+self.type)

        return self.valide
#        print ('fin_geom2:type_geom ', self.type, typegeom)


    def split_couleur(self, couleur):
        '''decoupe une ligne selon la couleur des sections'''
        geoms = dict()
        couleur = int(couleur)
        for i in self.lignes:
            for j in i.sections:
                coul_sect = j.couleur
                if couleur != -1 and coul_sect != couleur:
                    coul_sect = -1
                if coul_sect not in geoms:
                    geoms[coul_sect] = Geometrie()
                geoms[coul_sect].ajout_section(j.dupplique(),False)
        for i in geoms:
            geoms[i].finalise_geom('2') # on force en ligne
#        print ("decoupage en couleurs ", couleur, geoms, self)
        return geoms

    def extract_couleur(self,couleur):
        ''' recupere les sections d'une couleur'''
        geom = Geometrie()
        couleur = int(couleur)
        for i in self.lignes:
            for j in i.sections:
                if j.couleur == couleur:
                    geom.ajout_section(j.dupplique(),False)
        return geom

    def has_couleur(self,couleur):
        '''retourne True si la couleur existe dans l'objet'''
        couleur = int(couleur)
        liste_couleurs = {j.couleur for j in itertools.chain.from_iterable([i.sections for i in self.lignes])}
#        print('has_couleur',couleur, liste_couleurs, couleur in liste_couleurs)
        return couleur in liste_couleurs


    def forcecouleur(self, couleur1, couleur2):
        '''remplace une couleur par une autre'''
        couleur1 = int(couleur1)
        couleur2 = int(couleur2)
        for i in self.lignes:
            for j in i.sections:
                if j.couleur == couleur1:
                    j.couleur = couleur2

    def forceligne(self):
        '''force la geometrie en ligne pour des polygones'''
        if self.type == '3':
            self.type = '2'
        self.multi = len(self.lignes)-1

    def translate(self,dx,dy,dz):
        """decale une geometrie"""
#        print ("translate geom avant :", list(self.coords))
        fonction = lambda coords:list(i+j for i,j in zip(coords,(dx,dy,dz)))
        self.convert(fonction)
        return True
#        print ("translate geom aprest :", list(self.coords))

    def prolonge(self, longueur, mode):
        '''prolonge une multiligne'''
#        print("dans prolonge", longueur, mode)
        if self.type != '2':
            return False
        if mode > 10:
            for i in self.lignes:
                i.prolonge(longueur, mode-10)
        else:
            if mode % 2: # prolongation du debut
#                print("dans prolonge debut", longueur, mode)
                self.lignes[0].prolonge_debut(longueur)
            if mode >= 2:
                self.lignes[-1].prolonge_fin(longueur)
#        print("geom apres prolonge", list(self.coords))
#        print("longueur ",self.longueur)

    def forcepoly(self, force=False):
        '''convertit la geometrie des lignes en polygones en fermant de force'''
        if self.type == '2':
            valide = True
            for i in self.lignes:
                if not i.ferme:
                    valide = force and i.force_fermeture()

                if valide:
                    if i.aire < 0:
                        if self.polygones:
                            self.polygones[-1].ajout_contour(i)
                        else: i.inverse()
                        self.polygones.append(C.Polygone(i))
                    else:
                        self.polygones.append(C.Polygone(i))
            if valide:
                self.type = '3'
                self.multi = len(self.polygones)-1
            else:
                self.polygones = []


    @property
    def coords(self):
        ''' iterateur sur les coordonnees'''
        if self.null:
            return iter(())
        return itertools.chain(*[i.coords for i in self.composants])



    def convert(self, fonction, srid=None):
        ''' applique une fonction aux points '''
        for crd in self.coords:
            for i, val in  enumerate(fonction(crd)):
                crd[i] = val
        if srid:
            self.srid=str(int(srid))




    def set_2d(self):
        '''transforme la geometrie en 2d'''
        if self.dimension == 2:
            return
        self.dimension = 2
        for i in self.lignes:
            i.set_2d()
        if self.point:
            self.point.set_2d()


    def setz(self, val_z, force=False):
        '''force le z '''
        if self.dimension == 3:
            if not force:
                return
        self.dimension = 3
        for i in self.lignes:
            i.setz(val_z)
        if self.point:
            self.point.setz(val_z)



    def emprise(self):
        '''calcule l'emprise'''
        liste_coords = list(self.coords)
        xmin, xmax, ymin, ymax = 0, 0, 0, 0
        try:
            if liste_coords:
                xmin = min([i[0] for i in liste_coords])
                xmax = max([i[0] for i in liste_coords])
                ymin = min([i[1] for i in liste_coords])
                ymax = max([i[1] for i in liste_coords])
        except:
            print (liste_coords)
            print("erreur 3D")
        return (xmin, ymin, xmax, ymax)

    @property
    def longueur(self):
        '''longueur de la geometrie'''
        comp = self.composants
#        print (" calcul de la longueur", comp,list(i.longueur for i in comp) )
        return sum(i.longueur for i in comp) if comp else 0



    def isin(self,point):
        '''verifie si un point est a l'interieur'''
        if self.type < 3:
            return False

    def getpoint(self,numero):
        '''retourne le n ieme point'''
        n=0
#        print ('coordlist',self.type,list(self.coordlist()))
        for i in self.coords:
            if n==numero:
                return i
            n+=1
        return i


    def print_debug(self):
        '''affichage de debug'''
        print('debug: geom : geometrie', Geometrie)
        print('debug: geom : type: ', self.type, 'lignes', len(self.lignes))
        for i in self.lignes:
            i.print_debug()



class Erreurs(object):
    '''gere le stockage de erreurs sur un objet.'''
    def __init__(self):
        self.errs = []
        self.warns = []
        self.actif = 0

    def ajout_erreur(self, nature):
        ''' ajoute un element dans la structure erreurs et l'active'''
        self.errs.append(nature)
        self.actif = 2

    def ajout_warning(self, nature):
        ''' ajoute un element de warning dans la structure erreurs et l'active'''
        self.warns.append(nature)
        if self.actif == 0:
            self.actif = 1

    def reinit(self):
        '''reinitialise la structure'''
        self.__init__()

    def getvals(self):
        '''recupere les erreurs en format texte'''
        return '; '.join(self.errs)

    def __repr__(self):
        '''erreurs et warnings pour affichage direct'''
        return '\n'.join(('actif:'+ str(self.actif),'errs:' + self.getvals()))

class AttributsSpeciaux(object):
    '''gere les attibuts speciaux a certains formats '''
    def __init__(self):
        self.special = dict()

    def set_att(self, nom, nature):
        '''positionne un attribut special'''
        self.special[nom] = nature

    def get_speciaux(self):
        ''' recupere la lisdte des attributs speciaux'''
        return self.special

def noconversion(obj):
    ''' conversion geometrique par defaut '''
    return obj.attributs['#type_geom'] == '0'

