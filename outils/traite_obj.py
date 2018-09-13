# -*- coding: cp1252 -*-
# formats d'entree sortie
''' format osm '''

import os
import time
import math as M
import sys
import itertools
import operator
from collections import defaultdict, namedtuple

#import numpy as np
POINT = namedtuple('pt',('x','y','z'))
POINT2D = namedtuple('pt2d',('x','y'))


class ProcessCore(object):
    '''ensemble d' outils d'indexation permettant les manipulations rapides des donnees'''
    def __init__(self, geom):
        self.triangles_par_points = None
        self.triangles_par_vect = None
        self.triangles_uniques = None
        self.geom = geom
        self.reindex()


    def reindex(self):
        ''' recalcule tous les indexes '''
        #------- triangles par point ----------
        self.triangles_par_points = defaultdict(set)
        self.triangles_par_vect = defaultdict(set)
        self.triangles_uniques = dict()
        for num, tr in self.geom.triangles.items():
            n1, n2, n3 = tr
            if n1 not in self.geom.points:
                print (" geometrie incoherente", num, n1)
            if n2 not in self.geom.points:
                print (" geometrie incoherente", num, n2)
            if n3 not in self.geom.points:
                print (" geometrie incoherente", num, n3)
            self.triangles_par_points[n1].add(num)
            self.triangles_par_points[n2].add(num)
            self.triangles_par_points[n3].add(num)
    #------- triangles par vect ----------
            self.triangles_par_vect[(n1, n2)].add(num)
            self.triangles_par_vect[(n2, n3)].add(num)
            self.triangles_par_vect[(n3, n1)].add(num)
            idtr = tuple(sorted(tr))
            if idtr in self.triangles_uniques:
                print ('attention triangles duppliques ', idtr,num,self.triangles_uniques[num])
            else:
                self.triangles_uniques[idtr] = num


    def _rem_or_del(self,n1,n2,num):

        if len(self.triangles_par_points[n1])>1:
            self.triangles_par_points[n1].remove(num)
        else:
            del self.triangles_par_points[n1]

        if len(self.triangles_par_vect[(n1, n2)])>1:
            self.triangles_par_vect[(n1, n2)].remove(num)
        else:
            del self.triangles_par_vect[(n1, n2)]

    def supp_triangle(self, num):
        '''maintient les index a jour pour la suppression d un triangle'''
        tr = self.geom.triangles[num]
        n1, n2, n3 = tr
        idtr = tuple(sorted(tr))
        self._rem_or_del(n1, n2, num)
        self._rem_or_del(n2, n3, num)
        self._rem_or_del(n3, n1, num)

        del self.triangles_uniques[idtr]


    def ajout_triangle(self, tr, num):
        '''maintient les index a jour pour la creation d un triangle'''
        idtr = tuple(sorted(tr))
#        if idtr in self.triangles_uniques:
#            print ('attention triangles duppliques ', idtr,num,self.triangles_uniques[num])
#            return False
        n1, n2, n3 = tr
        self.triangles_par_points[n1].add(num)
        self.triangles_par_points[n2].add(num)
        self.triangles_par_points[n3].add(num)
        #------- triangles par vect ----------
        self.triangles_par_vect[(n1, n2)].add(num)
        self.triangles_par_vect[(n2, n3)].add(num)
        self.triangles_par_vect[(n3, n1)].add(num)
        self.triangles_uniques[idtr] = num


    def check_triangle(self, tr):
        '''verifie si un triangle existe deja'''
        return tuple(sorted(tr)) not in self.triangles_uniques





class Geommesh(object):
    """ geometrie de mesh (maillage irregulier de triangles)"""
    suivant = (1, 2, 0)
    precedent = (2, 0, 1)
    courant = (0, 1, 2)
    def __init__(self,nom):
        self.nom = nom
        self.points = dict()
        self.triangles = dict()
        self.edges = None
        self.bords = []
        self.maxpoints = 0
        self.maxtriang = 0
        self.orig = None
        self.size = None
        self.indexes = None


    def init_process(self):
        '''cree les indexes internes necessaires au traitement'''
        self.indexes = ProcessCore(self)

# fonctions utilitaires ===================================

    def getused(self):
        """retourne une liste de points utilises"""
        return {j for tr in self.triangles.values() for j in tr }

    def del_unused(self):
        used = self.getused()
        ajeter = {i for i in self.points if i not in used}
        n = len(ajeter)
        for i in ajeter:
            del self.points[i]
        self.reindex()
        print(" points inutilises supprimes ",n)

    def reindex(self):
        self.bbox()
        self.indexes.reindex()



    def _vecteur(self, n1, n2):
        '''calcule le vecteur directeur d'une ligne'''
        p1 = self.points[n1]
        p2 = self.points[n2]
        return POINT(*(p2[i]-p1[i] for i in self.courant))

    def _vecteur_p(self, p1, p2):
        '''calcule le vecteur directeur d'une ligne'''
        return POINT(*(p2[i]-p1[i] for i in self.courant))

    def _normale(self, triangle):
        """calcule la normale a une face"""
        n1, n2, n3 = triangle
        v1 = self._vecteur(n1, n2)
        v2 = self._vecteur(n1, n3)
        return POINT(v1.y*v2.z-v2.y*v1.z, v1.z*v2.x-v2.z*v1.x, v1.x*v2.y- v2.x*v1.y)


    def _norme2(self,vect):
        """ calcule le carre de la norme"""
        return(vect.x*vect.x+vect.y*vect.y+vect.z*vect.z)


    def _alignes(self,p1,p2,p3):
        v1 = self._vecteur_p(p1,p2)
        v2 = self._vecteur_p(p1,p3)
        rapport = tuple(v1[i]/v2[i] for i in self.courant)
        return rapport


    def _recale_points(self, vref, indice, tolerance=0.01):
        '''cale les points proches de la ligne sur la ligne'''
        for num,p1 in self.points.items():
            try:
                if 0 <= p1[indice]-vref < tolerance:
                    p_final = POINT(*(p1[i] if i!=indice else vref+tolerance for i in self.courant))
                elif 0 <= vref -p1[indice] < tolerance:
                    p_final = POINT(*(p1[i] if i!=indice else vref-tolerance for i in self.courant))

                    self.points[num] = p_final
            except:
                print ('erreur',p1,indice,vref)


    def _getp_atv(self, n1, n2, vref, indice):
        '''calcule un point sur la ligne a l'ascisse x ou l'ordonnee'''
        p1 = self.points[n1]
        p2 = self.points[n2]
#        return p2

        vecteur = POINT(*(p2[i]-p1[i] for i in self.courant))
        nv = p2[indice]-p1[indice]
#
#        if abs(p1[indice]-vref) < (0.01):
#            p_final = POINT(*(p1[i] if i!=indice else vref for i in self.courant))
#            self.points[n1] = p_final
#            return p_final
#
#        if abs(ev)<0.01 or abs(nv) < 0.01: # cas particulier de la micoface dans une direction on deplace le point
#            p_final = POINT(*(p2[i] if i!=indice else vref for i in self.courant))
#            self.points[n2] = p_final
#            return p_final

        rapp = (vref - p1[indice]) / nv

        p_final = POINT(*(p1[i] + vecteur[i]*rapp if i!=indice else vref for i in range(3)))

        return p_final



#========================= ajout suppression delements ===================
    def supp_triangle(self, num):
        '''supprime un triangle'''
        if self.indexes:
            self.indexes.supp_triangle(num)
        del self.triangles[num]


    def ajout_triangle(self, triangle, force=False):
        """ ajoute un triangle a la liste"""

        if len(set(triangle))!=3: # triangle degenere
            return True
        if self.indexes.check_triangle(triangle):
            num = self.maxtriang
            if not force:
                triangle = self.validetriangle(triangle)
            if not triangle:
                return False
            self.triangles[num] = triangle
            self.indexes.ajout_triangle(triangle,num)
            self.maxtriang += 1
        return True


    def mod_triangle(self, num, valeurs, force=False):
        """ modifie un triangle a la liste"""
        tr_orig = self.triangles[num]
        self.supp_triangle(num)
        if self.ajout_triangle(valeurs,force):
            return True
#        self.ajout_triangle(tr_orig, force=True)


    def ajout_point(self, point):
        '''ajoute un point a la liste des points'''
        num = self.maxpoints
        self.points[num] = point
        self.maxpoints += 1
        return num


# manipolation de triangles ===================================

    def get_triangles(self, n1, n2):
        """ recupere les triangles associe a un segment"""
        tpl = self.indexes.triangles_par_vect
        return tpl.get((n2, n1),{}) | tpl.get((n1, n2),{})


    def coupe_triangle_en_2(self, cp1, numtriang, n1, n2):
#        print (" decoupage triangle en 2", cp1, numtriang)
        triangle = self.triangles[numtriang]
        self.supp_triangle(numtriang)
        if n1 == triangle[0]:
            self.ajout_triangle([n1, cp1, triangle[2]], force=True)
            self.ajout_triangle([triangle[2], cp1, n2], force=True)
        elif n1 == triangle[1]:
            self.ajout_triangle([n1, cp1, triangle[0]], force=True)
            self.ajout_triangle([triangle[0], cp1, n2], force=True)
        elif n1 == triangle[2]:
            self.ajout_triangle([n1, cp1, triangle[1]], force=True)
            self.ajout_triangle([triangle[1], cp1, n2], force=True)


    def decoupe_ligne(self, n1, n2, vref, indice):
        if self.points[n1][indice] == vref:
            return
        if self.points[n2][indice] == vref:
            return
        p1 = self._getp_atv(n1, n2, vref, indice)
        cp1 = self.ajout_point(p1)

        listetriang = tuple(self.indexes.triangles_par_vect.get((n1,n2),()))
        if listetriang:
            numtriang = listetriang[0]
            self.coupe_triangle_en_2(cp1, numtriang, n1, n2)

        listetriang = tuple(self.indexes.triangles_par_vect.get((n2,n1),()))
        if listetriang:
            numtriang2 = listetriang[0]
            self.coupe_triangle_en_2(cp1, numtriang2, n2, n1)



    def cree_ligne_decoupe(self, vref, indice):
        """cree une ligne de decoupe nette"""
        segs = []
        self._recale_points(vref, indice)
        for seg in self.indexes.triangles_par_vect:
            n1, n2 = seg
            v1, v2 = self.points[n1][indice], self.points[n2][indice]
            if (v1 < vref and v2 > vref) or (v2 < vref and v1 > vref):
                segs.append(seg)
        print(len(segs), "triangles a decouper")
        for seg in segs:
            n1, n2 = seg
            self.decoupe_ligne(n1, n2, vref, indice)

    def decoupe(self, vref, fonc, indice):
        ajeter = []
        self.cree_ligne_decoupe(vref, indice)
        for num, tr in self.triangles.items():
            # on jette les faces en dehors et on fait la liste des faces intersectees
            ok = any(fonc(self.points[i][indice], vref) for i in tr)
            if not ok:
                ajeter.append(num)

        for i in ajeter:
            self.supp_triangle(i)
#        self.del_unused()





    def bbox(self):
        ''' calcule la bounding box '''
        used = [self.points[i] for i in self.getused()]
#        self.del_unused()
#        self.orig = POINT(*(min((pt[i] for pt in self.points.values())) for i in self.courant))
#        self.size = POINT(*(max((pt[i] for pt in self.points.values()))-self.orig[i] for i in self.courant))
        self.orig = POINT(*(min((pt[i] for pt in used)) for i in self.courant))
        self.size = POINT(*(max((pt[i] for pt in used))-self.orig[i] for i in self.courant))
        print('taille modele ' ,self.size, 'point min: ',self.orig)

    def getbbox(self, garde):
        if self.orig is None:
            self.bbox()
        orig = POINT(*(self.orig[i]-garde for i in range(3)))
        size = POINT(*(self.size[i]-garde for i in range(3)))
        return orig, size

    def clean_triangles_byindex(self, n2, n1):
        # triangles contenant n2
        for num in list(self.indexes.triangles_par_points[n1]):
            tr = self.triangles[num]
            if n2 in tr: # triangle degenere: on degage
#                print (n1,'->',n2,'triangle degenere',tr)
                self.supp_triangle(num)
            else:
                tr2 = [i if i != n1 else n2 for i in tr ]
                self.mod_triangle(num, tr2)
#                print (n1,'->',n2, 'modification' ,tr, '->', tr2)
#                print ("nettoyage",n1,"->",n2,tr,tr2)
#                geom.verifie_sens()
        del self.points[n1]
#        self.verifie_sens()




    def controle_ponctuel(self,p1,p2):
        """controle la coherence des faces suivant un vecteur"""
        positions = ((0,1),(1,2),(2,0))
        ltr1 = self.triangleindex[p1]
        ltr2 = self.triangleindex[p2]
        communs = ltr1 & ltr2
        if len(communs)==1:
            print (" cest un bord",p1,p2)
        elif len(communs)==2:
            tr1, tr2 = communs
#            if [p1,p2] in


    def corrige_sens(self):
        err2 = [(n,i) for n, i in self.indexes.triangles_par_vect.items() if len(i) > 1]
        print(" nombre d erreurs" ,len(err2))
        for err in err2:
            cote, faces = err
            tmptriangles = []
            for num in list(faces):
                tmptriangles.append(self.triangles[num])
                self.supp_triangle(num)
            for triangle in tmptriangles:
                self.ajout_triangle(triangle)
        print(" nombre d erreurs apres" ,len(err2))


    def verifie_sens(self):
        '''verifie que les faces jointives en un point sont coherentes'''

        erreurs = [i for i in self.indexes.triangles_par_vect.values() if len(i) > 1]
        if erreurs:
            err2 = [(n,i) for n, i in self.indexes.triangles_par_vect.items() if len(i) > 1]
            print ('vecteurs incoherents ', erreurs, 'sur' , len(self.indexes.triangles_par_vect))
            for i in err2:
                clef,vals = i
                for j in vals:
                    print (clef,j,self.triangles[j])
            return

        print ("verifie sens:objet propre ")

    def triangles_degeneres(self):
        print( 'recherche de triangles degeneres')
        nd = 0
        for i in self.triangles.values():
            tpts = set(i)
#            print('triangle etudie',tpts)
            if len(tpts)!=3:
                nd+=1
                print('triangle dégénére',tpts)


    def supp_triangles_degeneres(self):
        print( 'recherche de triangles degeneres')
        nd = 0
        for i in self.triangles.values():
            tpts = set(i)
#            print('triangle etudie',tpts)
            if len(tpts)!=3:
                nd+=1
                print('triangle dégénére',tpts)




    def get_edgelist(self):
        ''' recupere la liste des brins de bord '''
#        self.reindex()
        vecteurs = self.indexes.triangles_par_vect
        edges = []
        bizarres = []
        for i in vecteurs:
            a, b = i
            if (b, a) not in vecteurs:
                edges.append(i)
            if len(vecteurs[i]) > 1:
                bizarres.append(i)
        self.edges = edges
        print('bords trouves',len(self.edges))
        print('trucs etranges ', len(bizarres))
#        print (self.edges)
        self.bizarres=bizarres
        return self.edges


    def get_edges2(self):
        bords=[]
        self.get_edgelist()
        if not self.bizarres:
            segments = {i:(i,j) for i,j in self.edges}
#            print( "segments", segments)
            while segments:
                nd,sd = segments.popitem()
                bord = [sd]
#                print ("bord",bord)
                bords.append(bord)
                while bord[-1][1] in segments:
                    bord.append(segments.pop(bord[-1][1]))
#                    print ("bord",bord)
        self.bords = bords





    def calcule_connectivite(self, triangle):
        '''calcule la connectivite d'un triangle existantou a venir'''
        connect = 0
        ref = self.indexes.triangles_par_vect
        for i,j in zip(self.courant,self.suivant):
            connect += 1 if (triangle[i],triangle[j]) in ref else 0
            connect += 10 if (triangle[j],triangle[i]) in ref else 0
        reverse = connect < 10
        if connect >10:
            if connect% 10:
                print ('attention sens incoherent',connect, triangle)
                for i,j in zip(self.courant,self.suivant):
                    if (triangle[i],triangle[j]) in ref:
                        print (triangle[i],triangle[j],'->',ref[triangle[i],triangle[j]])
                    if (triangle[j],triangle[i]) in ref:
                        print (triangle[j],triangle[i],'->',ref[triangle[j],triangle[i]])

            else:
                connect = connect/10
        return connect, reverse


    def validetriangle(self, triangle):
        """on essaye de mettre le triangle dans le bon sens"""
        p1,p2,p3 = triangle
        connect, reverse = self.calcule_connectivite(triangle)
        if reverse:
            triangle.reverse()
        return triangle



    def cycle2(self, trou):
        '''decale un bord pour boucher les trous malsains'''
#        print ('ccycle2',trou)
        trou.insert(0,trou.pop())
#        print ('ccycle2',trou)




    def trytoclose2(self, trou, force=False):
        ''' reduit un trou'''
#        print ('traitement trou', len(trou), trou)
        start_num = self.maxtriang
        if len(trou) == 3:
            triangle = [trou[0][0],trou[0][1],trou[2][0]]
#            print ("triangle",triangle)
            connect, reverse = self.calcule_connectivite(triangle)
            if connect != 3:
                print ('erreur connectivite ',triangle)
                print ('connectivite trouvee ',connect, triangle)
            self.ajout_triangle(triangle)
#            self.verifie_sens()
            return []
#        print ('traitement trou', len(trou), trou)
        taille = 0
#        self.cycle2(trou)
        while len(trou) != taille:
            tr2 = []
            taille = len(trou)
            for i in range(0, taille-1, 2):
                triangle = [trou[i][0], trou[i][1], trou[i+1][1]]
                connect, sens = self.calcule_connectivite(triangle)
                if connect != 2:
                    if connect == 3 and taille == 3:
                        self.ajout_triangle(triangle)
                        return
                    else:
                        print ('connectivite trouvee ',connect, triangle, len(trou), trou)
                        tr2.append(trou[i])
                        tr2.append(trou[i+1])
                else:
                    self.ajout_triangle(triangle)
#                    print ("creation triangle ",triangle)
                    tr2.append((triangle[2],triangle[0]))
            if i+2 < taille:
#                print ("ajout",i , len(trou),trou[-1])
                tr2.append(trou[-1])
            if tr2 and len(tr2)<3:
                print("trou invalide", tr2, i)
                raise
#            print ("apres", tr2)
            trou = tr2
        if tr2 and not force:
            # nettoyage
            end_num = self.maxtriang
            for i in range(start_num,end_num):
                if i in self.triangles:
                    self.supp_triangle(i)

        return tr2


    def close_avec_point(self, residu):
        '''la on a un trou rebelle on va essayer de creer un point au centre'''
        pts = [self.points[i[1]] for i in residu]
        print ('------------trou rebelle on rajoute un point pour le calmer ',residu)
        npt = len(residu)
        ptref = POINT(sum(a.x for a in pts)/npt, sum(a.y for a in pts)/npt, sum(a.z for a in pts)/npt)
        num = self.ajout_point(ptref)
        for i in residu:
            self.ajout_triangle([i[0],i[1],num])



    def edge_closer2(self, maxhole):
        ''' essaye de fermer les trous '''
        bords2 = []
        petits_trous = []
        for i in self.bords:
            if len(i) > maxhole:
                print( 'trou trop gros ',len(i))
                bords2.append(i)
            else:
                petits_trous.append(i)

        for i in petits_trous:
            trou =i[:]
            nbessais = 0
            residu = 1
            while  residu and nbessais < len(trou):
                residu = self.trytoclose2(trou[:])
                self.cycle2(trou)
                nbessais += 1
            if residu:
                print ("----------------trou ingerable",trou)
                residu = self.trytoclose2(trou[:], force=True)
                self.close_avec_point(residu)
#                bords2.append(trou)

        self.bords = bords2



    def ferme_bord(self, bord, zsocle):
        segf = bord[-1]
        pfin = segf[1]
        pfbas = self.ajout_point(POINT(self.points[pfin].x, self.points[pfin].y, zsocle))
        segvf = (pfin, pfbas)
        segd = bord[0]
        pdeb = segd[0]
        pdbas = self.ajout_point(POINT(self.points[pdeb].x, self.points[pdeb].y, zsocle))
        segvd = ( pdbas, pdeb)
        segh = (pfbas, pdbas)
        bord.extend([segvf,segh,segvd])




    def cresocle(self, zsocle, reverse=False):
        'cree le socle '
        print('socle : nombre de bords', len(self.bords), [len(i) for i in self.bords])
        for b1 in self.bords:
            cotes = self.eclate_bord(b1, self.orig.x, self.orig.x+self.size.x, self.orig.y, self.orig.y+self.size.y)
            for bord,ind in cotes:
                
                segp = None
                print('socle : traitement bord', len(bord), bord[0],bord[-1])
                self.ferme_bord(bord, zsocle)
                print('socle : fermeture', len(bord), bord[0],bord[-1])
                ptref = self.passeligne2d(bord, ind)
                lenp = 0
#                sens = self.aire2d(bord)
                while len(bord)> 3 and len(bord)!=lenp :
                    lenp = len(bord)
                    bord2 = []
                    for seg in bord:
                        if segp is None:
                            segp=seg
                            continue
                        print ("detection oreille",segp,seg, self.tourne_a_droite( ptref, segp, seg))
                        if self.tourne_a_droite( ptref, segp, seg):
                            triangle = (segp[1], segp[1], segp[0])
                            self.ajout_triangle(triangle)
                            segp = (segp[0],seg[1])
                            bord2.append(segp)
                        else:
                            bord2.append(segp)
                            segp = seg
                    bord = bord2




    def trouve_debut(self,bord):
        '''trouve le debut du bord pour calculer corectement le debut est xmin,ymin'''
        debut = None
        ref = self.orig
        for i, seg in enumerate(bord):
            ptbord = self.points[seg[0]]
#            print ('pt_bord',ptbord,ref)
            if ref.x == ptbord.x and ref.y == ptbord.y:
                debut = i
                break
        if debut is None:
            print( 'probleme de debut: pas de debut')
        else:
            print ('debut_trouve', debut, self.points[bord[debut][0]])
            bord2 = bord[debut:]+bord[:debut-1]
            return bord2
        raise


    def decoupe_bord(self,bord,vref,indice):
        '''decoupr un bord en 4 blocs suivant les axes'''
        cote=[]
        for n, seg in enumerate(bord):
            if self.points[seg[0]][indice] == vref and self.points[seg[1]][indice] == vref:
                cote.append(seg)
#        cote = [i for i in bord if self.points[i][indice] == vref]
        print ('taille bord trouve ',len(cote), vref, indice)
        return cote

#    def tourne_a_droite(self, p1, p2, p3, ind):
#        """determine si p1,p2 er p2,p3 tournent a droite"""
#        pt1 = self.points[p1]
#        pt2 = self.points[p2]
#        pt3 = self.points[p3]
#        v1x = pt2[ind]-pt1[ind]
#        v1y = pt2.z-pt1.z
#        v2x = pt3[ind]-pt1[ind]
#        v2y = pt3.z-pt1.z
#        det = v1x*v2y - v1y*v2x
#        return det<0
#    def map2D(self, bord, ind):
#        """cree un mapping en 2d pour un bord"""
#        2dmap = {i:self.passe_2d(i, ind) for i in bord}
#        return 2dmap
    
    

    def passe_2d(self, num, ind):
        ''' passe en 2d dans un plan vertical x ou y '''
        pnt = self.points.get(num)
        return POINT2D(pnt[ind],pnt.z) if pnt else None

    def aire2d(self, pt1, pt2, pt3):
        '''calcule une aire orientee du triangle'''
        return (pt2.x-pt1.x)*(pt2.y-pt1.y) + (pt3.x-pt2.x)*(pt3.y+pt2.y-2*pt1.y) + (pt1.x-pt3.x)*(pt3.y-pt1.y)

    def aire_bord2d(self, map2d, bord):
        '''calcule une aire orientee d'un bord vertical'''

        seg1 = bord[-1]
        aire = 0
        for seg2 in bord:
            pt1 = map2d[seg1[0]]
            pt2 = map2d[seg1[1]]
            pt3 = map2d[seg2[1]]
            aire += self.aire2d(pt1, pt2, pt3)
            seg1 = seg2
        return aire



    def passeligne2d(self, liste, ind):
        '''passe une ligne 3d dans un plan vertical en 2d avec z=>y'''
        return {i[1]:self.passe_2d(i[1], ind) for i in liste}

    def tourne_a_droite(self, map2d, seg1, seg2):
        """Tests whether the turn formed by A, B, and C is ccw"""
        pt1 = map2d[seg1[0]]
        pt2 = map2d[seg1[1]]
        pt3 = map2d[seg2[1]]
        return (pt2.x - pt1.x) * (pt3.y - pt1.y) > (pt2.y - pt1.y) * (pt3.x - pt1.x)


    def danstriangle2d(self,pt, pt1, pt2, pt3, airet=None):
        '''determine si un point est dans un triangle'''
        if airet is None:
            airet = self.aire2d(pt1, pt2, pt3)
        if not airet:
            return False
        val = self.aire2d(pt, pt1, pt2) + self.aire2d(pt, pt2, pt3) + self.aire2d(pt, pt3, pt1)
#        print("dans triangle:", val, val/airet)
        if val/airet > 0.5:
            return False
        return True

    def triangle_vide(self, pt1,pt2,pt3, liste):
        '''determine si le triangle contient un point de la liste'''


        xmin = min((pt1.x, pt2.x, pt3.x))
        xmax = max((pt1.x, pt2.x, pt3.x))
        ymin = min((pt1.y, pt2.x, pt3.y))
        ymax = max((pt1.y, pt2.x, pt3.y))

        airet = self.aire2d(pt1, pt2, pt3)
#        print ('aire triang',airet)

        retour = True
        for pt in liste:
            if pt.x < xmin or pt.y < ymin or pt.x > xmax or pt.y > ymax:
                continue
            if self.danstriangle2d(pt, pt1, pt2, pt3, airet):

#            val = self.aire2d(pt,pt1,pt2) + self.aire2d(pt,pt2,pt3) + self.aire2d(pt,pt3,pt1)
#            print(" aire aux:", val, val/airet)
#            if val/airet > 0.9:
                return False
        return retour

    def centroide2d(self, pt1, pt2, pt3):
        return POINT2D((pt1.x+pt2.x+pt3.x)/3, (pt1.y+pt2.y+pt3.y)/3)


    def seg_en_dessous(self, ptref, liste):
        ''' determine le nombre de segments sous un point'''
        nb = 1
        for n, pt in enumerate(liste):
            if n == 0:
                continue
            prec = liste[n-1]
            if (prec.x < ptref.x < pt.x or prec.x > ptref.x > pt.x):
#                print ('trouve suspect')
#                raise
                if prec.y < ptref.y and pt.y < ptref.y:
                    nb += 1 # il est en dessous a coup sur
#                    print( 'trouve en dessous' ,n,'(',len(liste),')', prec,ptref,pt)
#                    print (liste)
#                    raise
                    continue
                if prec.y > ptref.y and pt.y > ptref.y:
                    continue # circulez y a rien a voir
                else:
                    pt1 = pt
                    pt2 = prec
                    if pt1.x > pt2.x:
                        pt1, pt2 = pt2, pt1
                    pt3 = POINT2D(pt2.x, pt1.y)
                    if self.danstriangle2d(ptref, pt1, pt2, pt3):
                        nb += 1 # il est en dessous a coup sur
#        print ('en dessous ', nb)
        return nb



    def affiche_bord2(self):
        print( 'affichage segments bord')

        for seg  in self.edges:
            print (seg, self.points[seg[0]],self.points[seg[1]])







    def ecrire_bord(self,bord,indice,cle):
        with open("test_bords.csv","a") as fich:
            for i in bord:
                pnt = self.points[i]
                fich.write(str(cle)+";"+str(pnt[indice])+";"+str(pnt.z)+"\n")

#    def traite_retours_bord(self,bord,indice, n=0):
#        ''' on ajuste le bord pour faire du croissant '''
#        print(" traitement  bord",indice, len(bord))
#        autre = (1, 0)
#        if self.points[bord[0]][indice] > self.points[bord[-1]][indice]:
#            bord.reverse()
#        trouve = True
#        iteration = 0
#        saut = 0
#        while trouve and len(bord) > 3:
#            iteration += 1
#            trouve = False
#            bord2 = []
#            bord_2d = self.passeligne2d(bord,indice)
#            saut = 0
#            for i in range(2, len(bord)):
#                if saut:
#                    saut -= 1
#                    continue
##                print (" calcul",i)
#                p1 = bord[i-2]
#                p2 = bord[i-1]
#                p3 = bord[i]
#                bord2.append(p1)
#                tr2 = self.passeligne2d((p1, p2, p3),indice)
#                ptref = self.centroide2d(*tr2)
#                c1 = self.seg_en_dessous(ptref,bord_2d)
#                c2 = self.triangle_vide(*tr2, bord_2d)
##                print ('analyse bord ',n,iteration,'taille',len(bord),'pos',i, c1, c2)
#                if c1 % 2 and c2:
##                if self.seg_en_dessous(ptref,bord_2d) % 2 and self.triangle_vide(*tr2, bord_2d):
#                    print ("creation triangle" ,p1,p2,p3)
#                    self.ajout_triangle([p1,p2,p3])
#                    bord2.append(p3)
#                    saut = 2
#                    trouve = True
#            if bord2:
#                print ('bord2',n,iteration,bord2)
##                raise
#                bord=bord2
#        return bord





    def eclate_bord(self,bord, xmin, xmax, ymin, ymax):
        bord2 = self.trouve_debut(bord)
#        self.affiche_bord(bord2)
        bxmin = self.decoupe_bord(bord2, xmin , 0)
#        print ("xmin trouve",bxmin)
#        self.ecrire_bord(bxmin,1,"b1_ini")
#        bxmin = self.traite_retours_bord(bxmin,1,'xmin')
        bxmax = self.decoupe_bord(bord2, xmax , 0)
#        bxmax = self.traite_retours_bord(bxmax,1,'xmax')
#        self.ecrire_bord(bxmin,1,"b2")

        bymin = self.decoupe_bord(bord2, ymin , 1)
#        bymin = self.traite_retours_bord(bymin,0,'ymin')

        bymax = self.decoupe_bord(bord2, ymax , 1)
#        bymax = self.traite_retours_bord(bymax,0,'ymax')

        return ((bxmin,0),(bxmax,0),(bymin,1),(bymax,1))






    def decoupe_triangle(self,triangle, pointe, indice, cote):
        pass
        vectdef = tuple(i for i in triangle if i!=pointe)
        vect = self.vecteur(*vectdef)








    def ajuste_limite(self, geom2, direction, valeur):
        print ('ajustement limite', direction,valeur)
        pass







    def merge(self, geom2):
        mergedir = -1
        meshmerge = False

        if self.orig.x - geom.orig.x == self.size.x:
            meshmerge = True
            mergedir = 0
        elif self.orig.y - geom.orig.y == self.size.y:
            meshmerge = True
            mergedir = 1
        if meshmerge:
            self.ajuste_limite(geom, mergedir,self.orig[mergedir]+self.size[mergedir]-geom2.size(mergedir))

        offset = self.npoints
        self.points.extend(geom2.points)
        for tr in geom2.triangles:
            self.triangles.append(list(i+offset for i in tr))
        self.reindex()









def lire_obj(fichier):
    '''lit des objets a partir d'un fichier obj'''
    dd0 = time.time()
    nom = os.path.splitext(os.path.basename(fichier))[0]
    geom = Geommesh(nom)
    nlignes = 0
    nobj = 0

    prn = 100000
    aff = prn
    npoints = 0
    ntriang = 0
    with open(fichier,"r") as fich:
        for ligne in fich:
            nlignes += 1
            if nlignes == aff:
                print('obj: lignes lues', nlignes, 'objets:', nobj, 'en', int(time.time()-dd0),
                      's (', int(nobj/(time.time()-dd0)), ')o/s')
                aff += prn
            elements = ligne.split(" ")
#            print (" lus", elements)
            if elements[0] == "v":
                pt = POINT(*(float(i) for i in elements[1:]))
                geom.points[npoints] = pt
                npoints += 1

            elif elements[0] == "f":
                triang = list(int(i.split('/')[0])-1 for i in elements[1:])
                for i in triang:
                    if i > npoints-1:
                        print ('point out of range',triang)
                geom.triangles[ntriang] = triang
                ntriang += 1

    geom.maxpoints = npoints
    geom.maxtriang = ntriang
    print ("lu ",npoints,ntriang,nlignes)
    geom.bbox()
#    geom.triangleindexer()
    return geom

def ecrire_obj(geom, fichier):
    '''ecriture d un objet en obj'''
    ptmap = dict()
    with open(fichier,"w") as fich:

        used = geom.getused()
        npt = 0
        ntr = 0
        for i in used:
            npt+=1
            ptmap[i] = npt
#            print("point",i,points[i])
            fich.write("v %.4f %.4f %.4f\n" % tuple(geom.points[i]))
        for tr in geom.triangles.values():
            if tr:
                ntr += 1
                fich.write("f %d %d %d\n" % tuple((ptmap[j] for j in tr)))
    print ('ecriture finale',npt,ntr)

def limcase_1d(orig, case, casedef, num):
    ''' calcule la limite de la case'''
    casemin = orig[num] +case[num]*casedef[num]
    casemax = casemin + casedef[num]
    return casemin, casemax

def ranger(grille, pt, numero, orig, casedef):
    """range un point dans la grille"""
    pos = tuple(int((pt[i]-orig[i])/casedef[i]) for i in range(3))
    grille[pos].add(numero)

def limcase_3d(geom, grille, orig, casedef, tol):
    a_retenir = set()
    for case in grille:
#        print ('limites',case,len(grille),len(grille[case]))
        limites = []
        for i in range(3):
            limites.append(limcase_1d(orig, case, casedef, i))
        for npt in grille[case]:
            pt = geom.points.get(npt)
            if pt:
                for i in geom.courant:
                    vmin, vmax = limites[i]
                    if vmin > pt[i] or vmax < pt[i]:
                        print(" point mal range", i,vmin,pt[i],vmax, case, limcase_1d(orig, case, casedef, i))
                    if abs(pt[i]-vmin) < tol or abs(vmax-pt[i]) < tol:
    #                    print ('valeurs', i,vmin,pt[i],vmax)
                        a_retenir.add(npt)
                        break
#        print ('limites2',case,len(grille),len(grille[case]))
    return a_retenir


def clean_liste(geom, pts, tol2):
    detecte = 1
    npb=0
#    print ('clean_liste, points a traiter',len(pts))
    while detecte:
        detecte = 0
        for n1, n2 in itertools.combinations(pts, 2):
            p1 = geom.points.get(n1)
            p2 = geom.points.get(n2)
            if p1 and p2:
                vect = tuple(((p1[i]-p2[i]) for i in geom.courant))
                dist2 = sum((vect[i]*vect[i] for i in geom.courant))
                if dist2 < tol2:
                    detecte=1
    #                del geom.points[n2] # on supprime p2

    #                clean_triangles(n2,n1)
                    geom.clean_triangles_byindex(n2,n1)

                    npb += 1
#                    print ('suppression point ', n1,p1, n2, p2)
#                    break

#        geom.verifie_sens()

    return npb


def cleaner(geom, tol, liste=[], dec=0, indice=None ):
    """ nettoie les triangles de taille inferieure a la tolerance"""
    # definition de la grille
    garde = 10*tol+dec
    if indice is not None:
        # c est un nettoyage de ligne

        pass


    orig, size = geom.getbbox(garde)
    taille=len(liste) if liste else len(geom.points)
    optidecoup = int(M.sqrt(taille/100)+1)
    dx, dy, dz = geom.size
    casesize = (dx+dy)/(2*optidecoup)
    print ('decoupage optimal ', optidecoup, casesize)
    casedef = (dx/optidecoup, dy/optidecoup, dz/optidecoup)
    print ('decoupage reel ', casedef, orig)
    grille = defaultdict(set)
    used = geom.getused()
    npt = 0
    indices = liste if liste else range(len(geom.points))
    for numero in indices:
        if numero in used:
            npt = npt+1
            pt = geom.points[numero]
            ranger(grille, pt, numero, orig, casedef)

    print (npt+1, "points ranges", 'dans ', len(grille), 'cases')
    tol2 = tol*tol
    npb=0
    ncases = 0
    maxp = 0
    for case in grille:
        ncases += 1
        pts = grille[case]
        maxp = max(maxp,len(pts))
        npb += clean_liste(geom, pts, tol2)
        if ncases %1000 == 0:
            print (ncases, 'traitees', npb ,'(',maxp,')')
            maxp = 0

    pts_limites = limcase_3d(geom, grille, orig, casedef, tol)

    print ("problemes detectes:",npb)

    print ('pts_limites trouves ', len(pts_limites))
    return pts_limites

def rec_cleaner(geom, tol):
    ''' nettoyeur iteratif'''
    suite = 1
    residu = []
    garde = 10*tol
    orig, size = geom.getbbox(garde)
    lenp = 0
    while suite:
        residu = cleaner(geom, tol, liste=residu)
        suite = len(residu) > 100 and len(residu) != lenp
        lenp =len(residu)
    if lenp > 100: # on va essayer un autre truc chelou
        residu = cleaner(geom, tol, liste=residu, dec = 10*tol )
    npb2 = clean_liste(geom, residu, tol*tol)
    print ("problemes detectes en limite:",npb2)
    geom.del_unused()


def traite_boucle(nouveau, pt):
    boucle = list()
    pos = nouveau.index(pt)
    boucle = nouveau[pos:]
    nouveau[:] = nouveau[:pos]
    return boucle







def hole_detector2(geom, maxhole=100):
    '''detecte des trous'''
    geom.triangles_degeneres()
#    geom.edge_indexer()
    geom.get_edges2()
    geom.verifie_sens()
    print('segments de bord detectes:',len(geom.edges), len(geom.bords))


def hole_closer2(geom,maxhole=100):
    geom.edge_closer2(maxhole)
    geom.triangles_degeneres()
    print('segments de bord detectes:',len(geom.edges), "en",len(geom.bords) )
#    geom.affiche_bord2()


def recale(geom, dec, cote, abx=0, aby=0):
    if abx == 0:
        orig,taille = geom.getbbox(0)
        refx = orig.x+dec
        refy = orig.y+dec
    else:
        refx = abx
        refy = aby
    endx = refx + cote
    endy = refy + cote
    print ("recalage x", refx)
    geom.decoupe(refx, operator.gt, 0)
    print (" recalage y", refy)
    geom.decoupe(refy, operator.gt, 1)
    print (" recalage x", endx)
    geom.decoupe(endx, operator.lt, 0)
    print (" recalage y", endy)
    geom.decoupe(endy, operator.lt, 1)
    geom.del_unused()
    geom.reindex()
















orig_maillage = POINT(-231, -286, 120)

t1= time.time()
liste_a_lire = sys.argv[1].split(",")
fich1 = liste_a_lire[0]
tol = float(sys.argv[3])

geom = lire_obj(fich1)
geom.init_process()
#recale(geom, 1.5, 100)

#recale(geom, 20, 50)
t2=time.time()
#geom.verifie_sens()
#rec_cleaner(geom, tol)
#geom.reindex()

geom.verifie_sens()
geom.corrige_sens()
#
recale(geom, 0, 100, abx=-231, aby=-286 )
#recale(geom, 0, 50, abx=-231, aby=-276 )
print ('apres recale')
geom.reindex()
#recale(geom, 0, 3, abx=-231, aby=-286 )
#geom.verifie_sens()
#geom.verifie_sens()

#rec_cleaner(geom,0.01)
#
geom.verifie_sens()

#geom.affiche_bord()

#print ('second recalage ')
#recale(geom, -213, 50, abx=-213, aby=-280 )
#print ('3e recalage ')
#
#recale(geom, -213, 50, abx=-213, aby=-280 )
#print ('4e recalage ')
#recale(geom, -213, 50, abx=-213, aby=-280 )
#merged=0
#for fich in liste_a_lire[1:]:
#    merged += 1
#    g2 = lire_obj(fich)
#    orig_rel = POINT(*(g2.orig[i] - orig_maillage[i] for i in range(3)))
#    dex = orig_rel.x // 100+1
#    dey = orig_rel.y // 100+1
#    abx = orig_maillage.x + 100*dex
#    aby = orig_maillage.y + 100*dey
#    print ("clip dalle",  g2.orig, '->', abx,aby)
##    raise
##    rec_cleaner(g2, tol)
#    recale(g2, 0, 100, abx=abx, aby=aby)
#    rec_cleaner(g2,0.01)
#    geom.merge(g2)
##rec_cleaner(geom, tol/2)
##rec_cleaner(geom, tol)
#if merged:
#    rec_cleaner(geom,0.01)

t3=time.time()
#hole_detector(geom,100)
#hole_closer(geom,100)

hole_detector2(geom,100)
hole_closer2(geom,100)

#hole_detector(geom,100)
#hole_closer(geom,100)
#geom.affiche_bord()
geom.verifie_sens()
#print ('verif')
#hole_detector(geom)

geom.cresocle(130, reverse=True)


ecrire_obj(geom, sys.argv[2])
print ("temps de traitement %.1f s"% (time.time()-t1,))
print ("lecture %.1f s"% (t2-t1,))
print ("nettoyage %.1f s"% (t3-t2,))
print ("ecriture %.1f s"% (time.time()-t3,))
#