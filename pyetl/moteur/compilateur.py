# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:20:44 2015

@author: Claude unger

compilateur de regles : cree les enchainements de regles

"""
#from .interpreteur_csv import interprete_ligne_csv as interpreteur

def _affiche_debug(regles, debug):
    '''affichages de debug'''
    for regle in regles:
        if debug or regle.debug:
            regle.affiche()
            liens_num = regle.branchements.liens_num()
            liens_pos = regle.branchements.liens_pos()
            print("   compile: liens", regle.numero, '(', str(regle.index), ')', '-->',
                  [(i, liens_num[i], liens_pos[i]) for i in sorted(liens_num)])
            if '+' in regle.v_nommees['debug']:
                print('\n'.join([str((i, regle.branchements.brch[i]))
                                 for i in sorted(regle.branchements.brch)]))
            print("   compile: select", regle.selstd)





def _finalise(regle, debug):
    ''' gere les modifieurs de comportement'''
    if regle.store: # regle demandant un stockage de l'ensemble des entrees
        regle.setstore()
    if regle.final:
        regle.branchements.brch["ok:"] = None
    if regle.filter:
        regle.branchements.brch["sinon:"] = None
        regle.branchements.brch["fail:"] = None
        if debug:
            print('regle filtrante ', regle.ligne)


def _gestion_branchements(regles, position, debug):
    ''' positionne les branchements entre les regles '''
    niveau_courant = regles[position+1].niveau
    regle = regles[position]
    if debug:
        print("compil : regles liees niveaux: ", position, regles[position].niveau,
              regles[position+1].niveau)
    if regles[position+1].enchainement == 'ok:':
        regle.branchements.brch["ok:"] = regles[position+1]
    if debug:
        print('calcul enchainements ', regle)
        j = 0
    for j in range(position+1, len(regles)):
        if regles[j].niveau > niveau_courant:
            continue #niveaux superieurs on ne s'en occupe pas
        if regles[j].niveau < niveau_courant:
            regle.branchements.setclink(regles[j])
            break # on a atteint un niveau inferieur : c est fini
#        regle.branchements.brch.update({i:regles[j] for i in regles[j].enchainements
#                                 if regles[j].enchainement == i})
        if debug:
            print('examen', regles[j], regles[j].enchainement)
        for i in regle.branchements.brch:

            if i != 'ok:' and regles[j].enchainement == i:
                regle.branchements.brch[i] = regles[j]

#        for ench in regles[j].enchainements:
#            if regles[j].enchainement == regles[j].enchainements[ench]:
#                regle.branchements.brch[ench] = regles[j]

#        if regles[j].enchainement == regles[j].enchainements["sinon:"]:
#            regle.branchements.brch["sinon"] = regles[j]
#        if regles[j].enchainement == regles[j].enchainements["fail:"]:
#            regle.branchements.brch["fail"] = regles[j]
#        if regles[j].enchainement == regles[j].enchainements["next:"]:
#            regle.branchements.brch["next"] = regles[j]
    if debug:
        print("recherche", j, sorted(regle.branchements.liens_num()))


def _valide_blocs(regles, position, bloc):
    ''' validation de la structure en blocs '''
    bloc_courant = bloc
    regle = regles[position]
#    print("validation blocs", bloc)
    for regle_courante in regles[position+1:]:
        if regle_courante.mode == "fin_bloc":
            if bloc == bloc_courant:
                regle.branchements.brch["sinon:"] = regles[regle_courante.index+1]
                break
            else:
                bloc_courant -= 1
        if regle_courante.mode == "bloc":
            bloc_courant += 1
    if not regle.branchements.brch["sinon:"]:
        print("cmp:erreur structure de blocs:", regle.ligne, bloc)
        return False




def propage_liens(regles, start):
    '''propage les liens pour la gestion des indentations'''
    niveau_courant = regles[start+1].niveau
    for j in range(start+1, len(regles)):
        if regles[j].niveau < niveau_courant:
#                        setclink(regle, j)
            regles[start].branchements.setclink(regles[j])
            break




def compile_regles(mapper, regles, debug=0):
    ''' prepare l'enchainement des regles sous forme de liens entre regles '''
    if not regles:
        print('pas de regles a compiler')
        raise EOFError("pas de regles a compiler")

    if mapper.get_param("sans_sortie"):
        regle_sortir = mapper.interpreteur(";;;;;;;pass;;;;;pas de sortie", "", 99999)
    else:
        regle_sortir = mapper.interpreteur(";;;;;;;sortir;"+mapper.get_param("F_sortie")+
                                           ";"+mapper.get_param("nom_sortie")+
                                           ";;;sortie_defaut", "", 99999)
    regle_sortir.final = True

    regle_sortir.index = len(regles)
    regles.append(regle_sortir) # on mets la regle de sortie pour finir
#    print ('liste_regles',regles)
#    raise
    bloc = 0
    for i in range(len(regles)-1):
        regle = regles[i]


        if regles[i+1].niveau > regle.niveau: # ca se complique les regles sont liees
            _gestion_branchements(regles, i, debug)

        elif regles[i+1].niveau == regle.niveau:
            if regles[i+1].enchainement and regles[i+1].enchainement != 'ok:':
                # c'est une regle sinon ou fail ou next
                propage_liens(regles, i)
#                niveau_courant = regles[i+1].niveau
#                for j in range(i+1, len(regles)):
#                    if regles[j].niveau < niveau_courant:
##                        setclink(regle, j)
#                        regle.branchements.setclink(regles[j])
#                        break
            elif regles[i+1].nonext: # c est unbe suite d'acces
                for j in range(i+1, len(regles)):
                    if not regles[j].nonext:
                        regle.branchements.brch["next:"] = regles[j]
                        break


        regle.branchements.setclink(regles[i+1])
        regle.suivante = True
        if regle.mode == "bloc":
            bloc += 1
            _valide_blocs(regles, i, bloc)

        if regle.mode == "fin_bloc": # gestion de la structure
            bloc -= 1
        _finalise(regle, debug)
    _affiche_debug(regles, debug)
    return True
