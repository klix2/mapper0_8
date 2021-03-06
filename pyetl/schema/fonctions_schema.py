# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 09:28:45 2014

@author: 89965
ensembles de fonctions permettant de manipuler des schemas et des objets
"""
import copy
import logging
import datetime as D
#import re
from .elements.schemaclasse import SchemaClasse
#import logging
LOGGER = logging.getLogger('pyetl')
#from . import schema_interne as SCI
#
# schemas : description de la structure des objets
DEF_MOIS = {'Jan':'01', 'jan':'01', 'JAN':'01', 'January':'01',
            'Feb':'02', 'feb':'02', 'FEB':'02', 'February':'02',
            'Mar':'03', 'mar':'03', 'MAR':'03', 'March':'03',
            'Apr':'04', 'apr':'04', 'APR':'04', 'April':'04',
            'May':'05', 'may':'05', 'MAY':'05',
            'Jun':'06', 'jun':'06', 'JUN':'06', 'June':'06',
            'Jul':'07', 'jul':'07', 'JUL':'07', 'July':'07',
            'Aug':'08', 'aug':'08', 'AUG':'08', 'August':'08',
            'Sep':'09', 'sep':'09', 'SEP':'09', 'September':'09',
            'Oct':'10', 'oct':'10', 'OCT':'10', 'October':'10',
            'Nov':'11', 'nov':'11', 'NOV':'11', 'November':'11',
            'Dec':'12', 'dec':'12', 'DEC':'12', 'December':'12'
           }

NOMS_MOIS = {'01':'Jan', '02':'Feb', 'Mar':'03', 'Apr':'04', 'May':'05', 'Jun':'06',
             'Jul':'07', 'Aug':'08', 'Sep':'09', 'Oct':'10', 'Nov':'11', 'Dec':'12',}

DDEF = D.datetime(9999, 2, 28)
DFORM = {'in':'%Y/%m/%d %H:%M:%S.%f',
         'en':'%m-%d-%Y %H:%M:%S.%f',
         'fr':'%d-%m-%Y %H:%M:%S.%f'
        }

# ----------------fonctions de validation de contenu-----------------------
# --------------dates--------------------
def get_jma(date, sep):
    '''essaye d'extraire le jour et mois eyt annee d'une date'''
    def_mois = DEF_MOIS
    el_date1, el_date2, el_date3 = date.split(sep)
    fdate = 'inc'
    if len(el_date3) == 4 and el_date3.isnumeric(): # jj-mm-aaaa
        if el_date2.isnumeric() and el_date1.isnumeric():
            annee, mois, jour = el_date3, el_date2, el_date1
            fdate = 'fr'
        elif el_date2 in def_mois: #jj nom_mois aaaa
            annee, mois, jour = el_date3, def_mois[el_date2], el_date1
            fdate = 'fr'
    elif len(el_date1) == 4 and el_date1.isnumeric(): # aaaa-mm-jj
        if el_date2.isnumeric() and el_date3.isnumeric():
            annee, mois, jour = el_date1, el_date2, el_date3
            fdate = 'in'
        elif el_date2 in def_mois: #aaaa nom_mois jj
            annee, mois, jour = el_date1, def_mois[el_date2], el_date3
            fdate = 'fr'


    return annee, mois, jour, fdate

def _valide_jour(date, format_date):
    ''' teste si le jour est correct'''

    # on cherche le separateur:
    seps = r'-/\,:'
    sep = None
    for i in seps:
        if i in date:
            sep = i
            break
    if sep: # date avec separateur
        try:
            annee, mois, jour, fmt = get_jma(date, sep)
            if format_date == '' or format_date == fmt:
                return date
        except ValueError:
            return None
    else: # juste une annee
        if len(date) == 4:
            try: # test dates numeriques
                int(date)
                jour, mois, annee = '01', '01', date
#                print ('test dates ',val,repl)
            except ValueError:
                return None
        else:
            return None
    if annee:
        if format_date == 'fr':
            return '-'.join((jour, mois, annee))
        elif format_date == 'in':
            return '/'.join((annee, mois, jour))
        elif format_date == 'en':
            return '/'.join((mois, jour, annee))
    return None


def _valide_heure(heure):
    ''' controle le format d'une heure '''
    dec = 0
    milisecs = None
    if heure[-1] == 'M':
        if heure[-2] == "P": # format sur 12h
            dec = 12
        heure = heure[:-2]
    tmp = heure.split(':')
    if len(tmp) == 3:
        hrs, mins, secs = tmp
    elif len(tmp) == 4:
        hrs, mins, secs, milisecs = tmp
    else:
        return None
    if dec:
        hrs = '%2.2d'%(int(hrs)+dec)
    if milisecs and int(milisecs):
        return ':'.join((hrs, mins, secs, milisecs))
    return ':'.join((hrs, mins, secs))


def _valide_dates(val, format_dates=''):
    '''controle la validite de la definition d'une date et eventuellement la corrige'''

    err = ''
    if not val:
        return err, None

    date, heure = None, None
#    if '03-09-2015' in val:
#        print(" schema interne: validation date ",val)
    v_2 = val.strip().split(" ")
    taille = len(v_2)
    if taille == 1: # pas de blanc dans la date c'est un format numerique
        date = val
        heure = None
    elif taille == 2: # format date heure
        date, heure = v_2
    elif taille == 3: # format j m a ou a m j ou m j a...
        date = val
        heure = None
    elif taille == 4: # format j m a ou a m j ou m j a + heure
        dat1, dat2, dat3, heure = v_2
        date = '-'.join((dat1, dat2, dat3))
    if date:
        date = _valide_jour(date, format_dates)

    if heure:
        heure = _valide_heure(heure)

    if date and heure:
        return err, date+' '+heure
    if date:
        return err, date
    return err, ""

#--- enters----
def _valide_entiers(val):
    '''controle la validite d'un entier et modifie le type en entier long si necessaire'''
    err = ''
    repl = None
    changetype = ''
    try:
        int(val)
        if len(val) > 8:
            changetype = 'EL'
    except ValueError:
        try:
            v_1 = float(val)
            if int(v_1) == v_1: # c'etait un entier stocke sous forme de flottant
                repl = str(v_1)
#                        obj.attributs[i] = repl
            else:
                err = 'entier'
        except ValueError:
            err = 'entier'
    return err, repl, changetype


def info_schema(schemaclasse, request, nom=None):
    '''retourne des elements modifiables du schema'''
#    print('dans info_schema :',classe.nom,classe.info["type_geom"],classe.info["dimension"])
    if request in schemaclasse.info:
        return str(schemaclasse.info[request])

    elif request == "multigeom":
        return "1" if schemaclasse.multigeom else "0"

    elif request == "alias":
        return str(schemaclasse.alias)
    elif request == "pk":
        return str(schemaclasse.getpkey)
    elif request == "attribut":
        return "1" if nom in schemaclasse.attributs else "0"
    print("infoschema: commande inconnue ", schemaclasse, request)
#    raise


def set_val_schema(schemaclasse, nom, valeur):
    '''positionne des elements modifiables du schema.
    attention l'ensemble des objets partageant un schema est affecte'''

#    print('dans set_schema :', classe.nom, nom, valeur)
    schemaclasse.type_table = "i"

    if nom in schemaclasse.info:
        schemaclasse.info[nom] = str(valeur)
        return True


    if nom == "dimension":
        try:
            schemaclasse.info[nom] = int(valeur)
        except ValueError:
            print('dimension autorisee 0 2 3 et pas ->', valeur)

    elif nom == "alias":
        schemaclasse.alias = bool(valeur)

    elif nom == "pk":
        keys = valeur.split(',')
        schemaclasse.setpkey(keys)
    elif nom == "mode_sortie":
        schemaclasse.schema.mode_sortie = valeur

    else:
        print('erreur mode schema non pris en compte', nom)
        return False

    return True
#    print ('apres',classe.info['type_geom'], classe)


def copyschema(classe, ident, schema2, filiation=True):
    '''copie du schema d'une classe vers un nouveau schema avec gestion des conformites'''
    if not classe:
        print("erreur schema inexistant", ident)
        return None
    old_schema = classe.schema # on evite de recopier toute la structure
    old_fils = classe.fils
    old_regles_modif = classe.regles_modif
#    print ("copie schema ",ident,schema2.nom,classe.attributs)
    classe.schema = None
    classe.fils = []
    classe.regles_modif = set()
    groupe, nom = ident
    nouvelle_classe = copy.deepcopy(classe)
    nouvelle_classe.nom = nom
    nouvelle_classe.type_table = "i"
    nouvelle_classe.groupe = groupe
    nouvelle_classe.schema = schema2
    nouvelle_classe.objcnt = 0
    classe.schema = old_schema
    classe.fils = old_fils
    classe.regles_modif = old_regles_modif
    if filiation:
        old_fils.append(nouvelle_classe) # gestion des filiations de classes
    #n = 0
#    print ('nouvelle_classe',nouvelle_classe.identclasse,nouvelle_classe.attributs)
    for i in nouvelle_classe.attributs:
    # il faut verifier les conformites
        conf = nouvelle_classe.attributs[i].conformite
        if conf:
            #n = n+1
#            print ('copie conformite ',i,conf.nom if conf else "non reference")
            if conf.nom in schema2.conformites:
                # elle existe deja on se branche dessus
                nouvelle_classe.attributs[i].conformite = schema2.conformites[conf.nom]
                #n2 += 1
            else:
                schema2.conformites[conf.nom] = conf #on la stocke
    if schema2:
        schema2.ajout_classe(nouvelle_classe)
    return nouvelle_classe


def _gere_conformite_invalide(classe, atdef, val, mode):
    ''' gere le controle de type par rapport au schema'''
    repl = None
    erreurs = list()
    warnings = list()
    conf = atdef.conformite
    nom_schema = classe.schema.nom
    nom_classe = classe.nom
    #print( 'dans gestion ',classe,mode,val)
    if mode == 'supp_conf':
        atdef.type_att = 'T' # on supprime automatiquement la conformite
        LOGGER.warning("schema: "+nom_schema+" :suppression conformite "+nom_classe+'.'+
                       atdef.nom+' '+atdef.nom_conformite+' -> '+atdef.type_att+':'+str(val))
#        print("schema:", nom_schema, ":suppression conformite ", nom_classe, atdef.nom,
#              atdef.nom_conformite, '->', atdef.type_att, ascii(str(val)))

        warnings.append(nom_classe+'.' + atdef.nom +":-->" + val +
                        '<-- non conforme enum:suppression enum' +
                        atdef.type_att + " " + conf.nom + ' (' + nom_schema + ')')
        atdef.conformite = False
        atdef.nom_conformite = ''
    elif mode == 'change_conf':
        print("schema:", nom_schema, ": modification conformité ", atdef.nom,
              atdef.type_att, val)
        warnings.append(nom_classe + '.' + atdef.nom + ":-->" + val +
                        '<-- non conforme enum:modification enum' +
                        atdef.type_att + " " + conf.nom + ' (' + nom_schema + ')')
        conf.stocke_valeur(val, val, 0)
    elif mode == 'change_val':
        repl = conf.defaut

        warnings.append(nom_classe + '.' + atdef.nom + ":" + atdef.type_att + ' modifie :' + val +
                        '->' + repl + ' (' + nom_schema + ')')
    else:
        erreurs.append(nom_classe + '.' + atdef.nom + ":-->" + val +
                       '<-- non conforme enum: type:' +
                       atdef.type_att + " nom:" + conf.nom +' (' + nom_schema + ')')
    return repl, erreurs, warnings

def _valide_bool(orig, val):
    '''convertit un booleen en format interne'''
    btypes = {'elyx':{'t':'t', 'f':'f', '-1':'t','0':'f'},
              'def':{'t':'t', 'f':'f', 'True':'t', 'False':'f', '0':'t', '1':'f'}
              }
    try:
        valides = btypes[orig]
    except:
        valides = btypes['def']

    try:
        return '', valides[val], ''
    except KeyError:
        return 'booleen: '+val, val, 'T'


def _valide_type(classe, atdef, val):
    ''' gere le controle de type par rapport au schema'''
    repl = None
    err = ''
    if atdef.type_att == "D":# test dates
        err, repl = _valide_dates(val, '')
    elif atdef.type_att == "E" or atdef.type_att_base == 'E':# test numerique
        err, repl, changetype = _valide_entiers(val)
        if changetype:
            if classe.debug:
                print("modification type_entier ",
                      atdef.type_att, classe.schema.nom, classe.nom, atdef.nom, val)
                #w = 1
            if atdef.type_att == "E":
                atdef.type_att = "EL"
            atdef.type_att_base = "EL"
    elif atdef.type_att == "EL" or atdef.type_att == "S":
        err, repl, changetype = _valide_entiers(val)
        if err:
            err = err + ' long'
    elif atdef.type_att == "F":# test numerique
        try:
            float(val)
        except ValueError:
            err = 'flottant'
    elif atdef.type_att == "B":# test numerique
        err, val, changetype = _valide_bool(classe.schema.systeme_orig, val)
        if changetype:
            atdef.type_att = "T"

    else:
        print('type non gere ', atdef.type_att, classe.schema.nom, classe.nom, atdef.nom, val)
    return err, repl

def set_err(classe, obj, message, attendu, erreur, affich):
    ''' genere le message d'erreurs qui va bien'''
    idobj = '.'.join(obj.ident)
    if erreur == '#NOMSCHEMA':
        erreur = classe.schema.nom
    if affich:
        print('valide_schema: '+message % (idobj, attendu, erreur),
              classe.schema.nom, classe.identclasse)
    return message % (idobj, attendu, erreur)


def valide_schema(schemaclasse, obj, mode='', repl='inconnu'):
    ''' verifie si un objet est conforme a son schema '''
    #print 'dans valide_schema',obj.ident
    # validation des types geometriques
    erreurs = list()
    warnings = list()
    nom_classe = str(obj.ident[1])

    if obj.geom_v.valide:
        multigeom = obj.geom_v.multi
        srid = obj.geom_v.srid
        courbe = obj.geom_v.courbe
        if mode != 'strict': # on detecte s'il y a des courbes pour la sortie
            if multigeom:
                schemaclasse.multigeom = True
            if courbe:
                schemaclasse.info['courbe'] = '1'
            if srid != schemaclasse.srid:
                schemaclasse.sridmix = True
    else:
        if not obj.geom:
            obj.attributs['#type_geom'] = '0'
    if obj.attributs['#type_geom'] != schemaclasse.info["type_geom"]:
        if obj.attributs['#type_geom'] == '3' and schemaclasse.info["type_geom"] == '2':
            #ligne fermee on autorise et on corrige le type
            obj.geom_v.forceligne()
            obj.infogeom()
        else:
#            print(obj.ident, '---------------------- type geometrie non conforme a',
#                  schemaclasse.info["type_geom"], ':', obj.attributs['#type_geom'])
            erreurs.append(set_err(schemaclasse, obj,
                                   '%s type geometrie non conforme : attendu %s objet :%s',
                                   schemaclasse.info["type_geom"], obj.attributs['#type_geom'], 0))

    if obj.attributs['#type_geom'] != '0' and str(obj.dimension) != schemaclasse.info["dimension"]:
        if schemaclasse.autodim:
            #choix automatique de la dimension c'est le premier objet qui gagne
            schemaclasse.info["dimension"] = str(obj.dimension)
            schemaclasse.autodim = False
        else:
            if schemaclasse.force_dim: # on force la dimension
                warnings.append(set_err(schemaclasse, obj,
                                        '%s mode 3D modifie: force  %s objet: %s',
                                        schemaclasse.info["dimension"], obj.dimension, 0))

                if schemaclasse.info["dimension"] == "3":
                    obj.geom_v.setz(float(schemaclasse.v_3d), force=True)
                else:
                    obj.geom_v.set_2d()
                obj.infogeom()
                obj.geomnatif = False

            else:
                erreurs.append(set_err(schemaclasse, obj,
                                       '%s mode 3D non conforme: attendu  %s objet: %s',
                                       schemaclasse.info["dimension"], obj.dimension, 1))


    for i in schemaclasse.attributs:
        val = obj.attributs.get(i)
        atdef = schemaclasse.attributs[i]
        err = 0 #c=self.schema.conformites.get(self.attributs[i].type_att,'')
        if not val:
            if atdef.oblig:
                if mode == 'strict':
                    erreurs.append(set_err(schemaclasse, obj, '%s.%s obligatoire: %s',
                                           i, '#NOMSCHEMA', 1))
                else:
                    warnings.append(set_err(schemaclasse, obj, '%s.%s obligatoire: %s',
                                            i, '#NOMSCHEMA', 0))
#                    erreurs.append(classe+'.'+i +' obligatoire('+nom_schema+')')
        elif atdef.conformite:
            if not atdef.conformite.valide_valeur(val):
                #print ('conformite erronee',val,atdef.conformite.valide_valeur(val))
                repl, errs, warns = _gere_conformite_invalide(schemaclasse, atdef, val, mode)
                if repl:
                    obj.attributs[i] = repl
                warnings.extend(warns)
                erreurs.extend(errs)
        elif atdef.type_att == 'T':
            continue
        else: # validation des types
            err, repl = _valide_type(schemaclasse, atdef, val)
            if repl is not None:
                obj.attributs[i] = repl

        if err:
            nom_schema = schemaclasse.schema.nom
            if mode == 'supp_conf':
                atdef.type_att = 'texte'
                warnings.append(nom_classe+'.'+i +":-->"+ val+'<-- non conforme :'+
                                atdef.type_att+' ('+nom_schema+') '+str(err))
            else:
                erreurs.append(nom_classe+'.'+i +":-->"+ val+'<-- non conforme :'+
                               atdef.type_att+' ('+nom_schema+') '+str(err))

    if warnings:
        if obj.attributs.get('#warnings', ''):
            obj.attributs["#warnings"] = obj.attributs['#warnings'] + '+' + '+'.join(warnings)
        else:
            obj.attributs["#warnings"] = '+'.join(warnings)
        LOGGER.info("schema: warning validation %s %s :-> %s", schemaclasse.schema.nom,
                    schemaclasse.groupe, '+'.join(warnings))

    if erreurs:
        if obj.attributs.get('#erreurs', ''):
            obj.attributs["#erreurs"] = obj.attributs['#erreurs']  + '+' + '+'.join(erreurs)
        else:
            obj.attributs["#erreurs"] = '+'.join(erreurs)

        LOGGER.info("schema: erreurs validation %s %s :-> %s", schemaclasse.schema.nom,
                    schemaclasse.groupe, '+'.join(erreurs))
        return False
    return True




def ajuste_schema_classe(schemaclasse, obj, taux_conformite=0):
    ''' mets a jour la definition du schema a partir de la structure d'un objet
    le taux de conformite est le nombre maxi de valeurs distinctes
    autorisees pour une enumeration'''
    #print conf
    if obj.virtuel:
        return
    if obj.schema:
        schema_orig = obj.schema
        liste_attributs = schema_orig.get_liste_attributs(sys=True)
    else:
        schema_orig = None
        liste_attributs = [i for i in obj.attributs if i[0] != "#"]
    schemaclasse.setorig(obj.idorig)

    for nom in liste_attributs:
        attr = schemaclasse.attributs.get(nom)
        if not attr:
#            print ("ajuste: creation attribut",nom,taux_conformite)
            att_orig = None

            if schema_orig:
                att_orig = schema_orig.attributs.get(nom)
                if att_orig:
                    alias = att_orig.alias
                    nom_court = att_orig.nom_court
                else:
                    alias = ''
                    nom_court = ''
            else:
                alias = ''
                nom_court = ''
            attr = schemaclasse.stocke_attribut(nom, 'A', nb_conf=taux_conformite,
                                                alias=alias, nom_court=nom_court)
            if not attr:
                print('ajuste_schema: erreur stockage attribut',
                      schemaclasse.identclasse, nom)
            if att_orig:
#                attr.clef = att_orig.clef
#                attr.defindex = {i:j for i,j in att_orig.defindex.items()}
                attr.unique = att_orig.unique
        if nom in obj.text_graph:
            attr.graphique = True
        attr.ajout_valeur(obj.attributs.get(nom))
    type_geom = obj.attributs['#type_geom']
    dimension = obj.dimension
    multigeom = False
    courbe = False
    if not obj.geom_v.valide:
        obj.attributs_geom(obj)
    type_geom = obj.geom_v.type
    multigeom = obj.geom_v.multi
#    print("avant ajuste_schema:",schemaclasse.nom, "recup type_geom", type_geom,
#          schemaclasse.info["type_geom"], schemaclasse.objcnt, schemaclasse)

    courbe = obj.geom_v.courbe
    dimension = str(obj.geom_v.dimension)
    if schemaclasse.objcnt == 0: # on vient de le ceer
        if obj.geom_v.valide:
            schemaclasse.srid = obj.geom_v.srid
            schemaclasse.info["type_geom"] = obj.attributs['#type_geom']



    if obj.geom_v.srid != schemaclasse.srid:
        schemaclasse.sridmix = True
    if obj.attributs['#type_geom'] == '0' and schemaclasse.info["type_geom"] != '0':
        schemaclasse.geomnull = True
    elif not schemaclasse.info["type_geom"]:
        schemaclasse.info["type_geom"] = obj.attributs['#type_geom']
    elif schemaclasse.info["type_geom"] == '1':
        if obj.attributs['#type_geom'] > '1':
            print("classe incoherente mix 1 et ", type_geom)
    elif schemaclasse.info["type_geom"] == '2':
        if obj.attributs['#type_geom'] == '1':
            print("classe incoherente mix 2 et 1")
    elif schemaclasse.info["type_geom"] == '3':
        if obj.attributs['#type_geom'] == '1':
            print("classe incoherente mix 3 et 1")
        elif obj.attributs['#type_geom'] == '2':
            schemaclasse.info["type_geom"] = '2'


    if multigeom:
        schemaclasse.multigeom = True
    if courbe:
        schemaclasse.info['courbe'] = '1'
    schemaclasse.info["dimension"] = max(dimension, schemaclasse.info["dimension"])
    schemaclasse.type_table = "i"
    obj.setschema(schemaclasse)
#    print("apres ajuste_schema:",schemaclasse.nom, "recup type_geom", type_geom,
#          schemaclasse.info["type_geom"], schemaclasse.objcnt, schemaclasse)


def adapte_schema_classe(schema_classe_dest, schema_classe_orig):
    '''adapte les schemas de destination pour pas faire des incoherences
    (supprime les attributs obligatoites non existant dans la source)'''
    schema_classe_dest.adapte = True
    for i in list(schema_classe_dest.attributs.keys()):
        # on essaye de creer un attribut on regarde si on a le droit
        if i not in schema_classe_orig.attributs:
            att = schema_classe_dest.attributs[i]
            #on peut pas creer un obligatoire sautf si defaut (pas encore géré)
            if att.oblig:
                del schema_classe_dest.attributs[i]
                print('FSC: adapte_schema: attribut obligatoire inexistant supprime', i)




def ajuste_schema(schema, obj, conf=0):
    ''' deduit un schema a partir des objets'''

    ident = obj.ident
    schema.origine = 'G'
    classe = schema.setdefault_classe(ident)
    ajuste_schema_classe(classe, obj, conf)


def map_dest(mapp, id_orig):
    """retourne la destination du mapping"""
    id_dest = mapp.mapping_destination.get(id_orig)
    if id_dest:
        return id_dest
#    print ('mapping',mapp.mapping_destination)
    if id_orig[1] in mapp.mappings_ambigus:
        print(' mapping ambigu ', id_orig[1])
#        raise ValueError
        return None
    id_dest = mapp.mapping_class_destination.get(id_orig[1])
    return id_dest


def mapping(mapp, classes, id_cl):
    '''#retourne un identifiant complet et une origine complete'''
    #ci=cl
    if not id_cl[0]:
        #print ('recherche ',cl[0],cl[1])
        if id_cl[1] in mapp.mappings_ambigus:
            print(' mapping ambigu ', id_cl[1])
            return ''
        else:
            id_cl = mapp.mapping_classe_schema.get(id_cl[1], ('mapping non trouve', id_cl[1]))
            #print ('recuperation',ci,cl[1])
    if id_cl in mapp.mapping_origine:
        origine = mapp.mapping_origine[id_cl]
        destination = id_cl
    elif id_cl in mapp.mapping_destination:
        origine = id_cl
        destination = mapp.mapping_destination[id_cl]
    elif id_cl in classes:
        origine = ''
        destination = id_cl
    else:
        #print (' schema: mapping : classe inconnue ',cl)
        return ''
    return origine, destination

def analyse_interne(schema, mode='util', type_schema=None):
    '''verifie la coherence interne d'un schema et cree les listes croisees de conformites'''
    print ("analyse interne" , schema.nom,mode,type_schema)
    retour = False
    if type_schema and schema.origine not in type_schema:
        return False
    if mode == 'no':
        return False
    if mode == 'non_vide': # on teste si au moins une classe du schema contient un objet
        if not schema.rep_sortie:
            return False
        if not schema.classes:
            return False
        if max([cl.objcnt for cl in schema.classes.values()]) >= 1:
            retour = True
            for schema_classe in schema.classes.values():
                schema_classe.a_sortir = True
        else:
            return False
    elif mode == 'util':
        if not schema.rep_sortie:
            return False
        for schema_classe in schema.classes.values():
            if schema_classe.objcnt > 0:
                schema_classe.a_sortir = True
                retour = True
            else:
                schema_classe.a_sortir = False
    elif mode == 'init':
        schema.init = True
        for schema_classe in schema.classes.values():
            #on mets les geometrie a 0 sie elles ne sont pas definies
#            print('traitement info', schema_classe, schema_classe.info['type_geom'])
            if schema_classe.info['type_geom'] == 'indef':
                schema_classe.info['type_geom'] = '0'
        retour = True
    else:
        for schema_classe in schema.classes.values():
            schema_classe.a_sortir = True
        retour = True
    if retour:
        for conf in schema.conformites.values():
            conf.utilise = False
            conf.usages = []
            conf.poids = 0
        for schema_classe in schema.classes.values():
            if schema_classe.a_sortir:
                for att in schema_classe.attributs.values():
                    if att.nom_conformite:
                        conf = schema.conformites[att.nom_conformite]
                        att.conformite = conf
                        conf.utilise = True
                        conf.usages.append((schema_classe.groupe, schema_classe.nom, att.nom))
                        conf.poids += schema_classe.poids #sert pour la fusion de schemas
    if mode == 'fusion':
        schema.stock_mapping.mode_fusion = True
    return retour







def analyse_conformites(schema):
    '''en cas de schema autogénére analyse les conformites et essaye de les regrouper'''
    print("analyse conformites", schema.nom, len(schema.classes))
    schema.conf_deja_analyse = True
    for i in schema.classes:
        schem_c = schema.classes[i]
        for att in schem_c.attributs.values():
            if att.conf and att.valeurs:
                # on essaye de voir si c'est une vraie conformite :
                #nombre de valeurs dans les classes non nulles > a 50 % des objets
                # presence de classes a plus d'une valeur
                nbvide, nbunique, nbconf = 0, 0, 0
                nom_conf = schema.nom + "_" + att.nom
                confvalide = True
                for val in att.valeurs:
                    if val == '' or val == 0: # valeur vide
                        nbvide += att.valeurs[val]
                    #elif att.valeurs[v]==1 : nbunique +=1
                    else:
                        nbconf += att.valeurs[val]
                        if att.valeurs[val] == 1:
                            nbunique += 1
                if nbconf-nbunique < schem_c.objcnt*schema.taux_conformite/100:
                # en dessous du 1/3 des objets ca ne compte pas
                    astocker = False
                    confvalide = False
                    print("schema: conformite refusee : ", nom_conf, nbconf, '(',
                          schem_c.objcnt*schema.taux_conformite/100, ')', schem_c.objcnt,
                          nbvide, nbunique)
                else:
                    if nom_conf in schema.conformites:
                        astocker = False
                        if len(schema.conformites[nom_conf].stock) != len(att.valeurs):
                            astocker = True
                            print("schema: ecart longueur", nom_conf,
                                  len(schema.conformites[nom_conf].stock), schem_c.nom, att.nom,
                                  len(att.valeurs))
                            nom_conf = nom_conf + "_" + schem_c.nom
                        else:
                            for val1, val2 in zip(sorted(schema.conformites[nom_conf].stock.keys()),
                                                  sorted(att.valeurs.keys())):
                                if str(val1) != str(val2):
                                    astocker = True
                                    print("schema: ecart schema", val1, val2, nom_conf,
                                          schem_c.nom)
                                    nom_conf = nom_conf + "_" + schem_c.nom
                                    break
                    else:
                        astocker = True
                if astocker: # on cree la conformite
                    conf = schema.get_conf(nom_conf, type_c='T', mode=1)
#                    print('schema: creation conformite', nom_conf, len(att.valeurs))
                    num = True
                    for val in att.valeurs:
                        try:
                            float(val)
                        except ValueError:
                            num = False
                            break

                    if num:
                        key = float
                    else:
                        key = None

                    for k in sorted(att.valeurs, key=key):
                        conf.stocke_valeur(k, k, 1)
                    print("longueur stockee", nom_conf, len(schema.conformites[nom_conf].stock))
                if confvalide:
                    att.nom_conformite = nom_conf
                    att.type_att_base = 'T'
                    att.type_att = nom_conf
                    att.conformite = schema.conformites[nom_conf]

#        xx=schema.classes[i]
#        print ('analyse_classe: ',xx.nom,xx)
#        print ('\n'.join([str((a.nom,a.nom_conformite,a.type_att,a.type_att_base))
#               for a in xx.attributs.values()]))

def compare_attributs(source, dest):
    """compare des attributs"""
    ecart = False
    if source.type_att != dest.type_att:
        ecart = True
    elif source.multiple != dest.multiple:
        ecart = True
    elif source.graphique != dest.graphique:
        ecart = True
    elif source.nom_conformite != dest.nom_conformite:
        ecart = True
    elif source.defaut != dest.defaut:
        ecart = True
    elif source.alias != dest.alias:
        ecart = True
    elif source.oblig != dest.oblig:
        ecart = True
    elif source.taille != dest.taille:
        ecart = True
    elif source.dec != dest.dec:
        ecart = True
    elif source.ordre != dest.ordre:
        ecart = True
    elif source.nom_court != dest.nom_court:
        ecart = True
    elif source.unique != dest.unique:
        ecart = True
    elif source.def_index != dest.def_index:
        ecart = True

    return ecart


def compare_classes(schema, source, dest):
    """detecte les differences entre classes"""
    ident = source.getident()
    ecart = SchemaClasse(schema, ident)
    ecart.att_supp = set()
    ecart.att_modif = set()
    ecart.att_cre = set()
    existe = False
    if source.info != dest.info:
        ecart.info = dict(dest.info)
        existe = True
    for i in source.attributs():
        if i in dest.attributs:
            if compare_attributs(source.attributs[i], dest.attributs(i)):
                ecart.att_modif.add(dest.attributs(i))
                existe = True

        else:
            ecart.att_supp.add(i)
            existe = True

    for i in dest.attributs:
        if i not in source.attributs:
            ecart.att_cre.add(i)
            existe = True
    if existe:
        schema.ajout_classe(ecart)



def compare_schemas(schema, source, dest):
    """affiche la difference entre 2 schemas"""
    #phase 1 comparaison des schemas : classes manquantes ou en trop
    classes_a_creer = set()
    classes_a_supprimer = set()
    for i in source.classes:
        if i in dest.classes:
            compare_classes(schema, source.classes[i], dest.classes[i])
        else:
            classes_a_supprimer.add(i)
    for i in dest.classes:
        if i not in source.classes:
            classes_a_creer.add(i)
    #phase 2 comparaison des classes entre elles
