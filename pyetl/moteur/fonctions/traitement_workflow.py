
# -*- coding: utf-8 -*-
"""
Created on Fri Dec 11 14:34:04 2015

@author: 89965
fonctions de gestion de strucures diverses
"""
import os
import re
import zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import ftplib
from pyetl.formats.interne.objet import Objet

#
#def f_true(*_):
#    '''#aide||ne fait rien
#       #pattern||;;;pass;;||sortie
#    '''
#    return True
def f_pass(*_):
    '''#aide||ne fait rien et passe
        #pattern||;;;pass;;
        #test||obj||C1;X;;;C1;Z;;set||+sinon:;;;;;;;pass||+:;;;;C1;Y;;set||atv;C1;Y
    '''
    return True

def f_fail(*_):
    '''#aide||ne fait rien mais plante
        #pattern||;;;fail;;
        #test||obj||^;;;fail||+fail:;;;;C1;Y;;set||atv;C1;Y
    '''
#    print ("fail:prochaine regle",regle.branchements.brch["sinon"])
    return False

def f_return(regle, _):
    """#aide||sort d une macro
    #pattern||;;;quitter;;

    """
    if regle.macroenv:
        if regle.macroenv.next:
            regle.branchement["ok"] = regle.macroenv.next
    return True


def h_start(regle):
    """helper start"""
    regle.chargeur = True
    return True


def f_start(regle, _):
    """#aide||ne fait rien mais envoie un objet virtuel dans le circuit
    #pattern||;;;start;;
    #test||rien||^;;;start||^;;;reel||cnt;1
    """
    obj2 = Objet('_declencheur', '_autostart', format_natif='interne',
                 conversion='virtuel')
    regle.stock_param.moteur.traite_objet(obj2, regle.branchements.brch["next:"])
    return True


def h_end(regle):
    """helper final"""
    regle.final = True
    return True


def f_end(regle, obj):
    """#aide||finit un traitement sans stats ni ecritures
    #pattern||;;;end
    #test||notest
    """
    return True

def f_reel(regle, obj):
    """#aide||transforme un objet virtuel en objet reel
    #pattern||;;;reel;;
    #test||rien||^;;;start||^;;;reel||cnt;1
    """
#    print("dans reel",obj)

    if obj.virtuel:
        obj.virtuel = False
        return True
    return False


def f_virtuel(regle, obj):
    """#aide||transforme un objet reel en objet virtuel
    #pattern||;;;virtuel;;
       #test||obj;;2||V0;1;;;;;;virtuel||cnt;1

    """
    if obj.virtuel:
        return False
    obj.virtuel = True
    return True


def h_chargeur(regle):
    '''helper generique definissant une regle comme executable'''
    regle.chargeur = True
    return True

def f_abort(regle, obj):
    '''#aide||arrete le traitement
  #aide_spec||usage: abort,niveau,message
 #aide_spec1||1 arret du traitement de l'objet
 #aide_spec2||2 arret du traitment de la classe
 #aide_spec3||3 arret du traitement pour le module
 #aide_spec4||4 sortie en catastrophe
    #pattern||;;;abort;?N;?C
       #test||obj;point;2;||V0;1;;;;;;abort;1;;;||^X;0;;set||cnt;1

    '''
    niveau = regle.params.cmp1.val or regle.params.att_sortie.val
    message = regle.params.cmp2.val or regle.params.val_entree.val
    if message.startswith("["):
        message = obj.attributs.get(message[1:-1])
    if message:
        print('abort: arret du traitement ', message, regle.ligne)
    if niveau <= "4":
        raise StopIteration(niveau)
    exit(0)

def printfunc(regle, obj):
    """ gere le boulot de print pour choisir vers ou l on sort """
    txt = regle.params.cmp1.val or regle.params.att_sortie.val
    if txt and txt[0] == '[':
        cmp1 = obj.attributs.get(txt[1:-1])
    else:
        cmp1 = txt
    noms = regle.params.cmp2.val or regle.params.val_entree.val
#    print ('affichage noms',noms,regle.params.cmp2)
    if regle.params.att_entree.dyn:
        liste = obj.get_dynlisteval(noms=noms)
    elif regle.params.att_entree.val == "#geom":
        if not regle.params.cmp1.val:
            cmp1 = "geom:"
        return cmp1 + str(obj.geom)
    elif regle.params.att_entree.val == "#geomV":
        if not regle.params.cmp1.val:
            cmp1 = "geomV:"
        return cmp1 + obj.geom_v.__repr__()
    else:
        liste = obj.get_listeattval(regle.params.att_entree.liste, noms=noms)
    if len(liste) > 1:
        return cmp1+','.join(liste)
    return cmp1+obj.attributs.get(regle.params.att_entree.val, regle.params.val_entree.val)



def h_sample(regle):
    '''prepare les parametres du sampler'''
    regle.samplers = defaultdict(int)
    regle.clef = regle.params.att_entree.val
    regle.vmin = regle.params.cmp2.num if regle.params.cmp2.num else 0
    regle.vmax = regle.params.cmp2.definition[0] if regle.params.cmp2.definition else 0
    regle.pas = int(regle.params.cmp1.num) if regle.params.cmp1.num else 1



def f_sample(regle, obj):
    '''#aide||recupere un objet sur x
    #pattern||;;?A;sample;N;N:N
    #pattern2||;;?A;sample;N;?N
    #test||obj;;10||^;;#classe;sample-;7;1||atv;V0;7
    #test2||obj;;10||^;;;sample-;7;1||atv;V0;7
    '''
    clef = obj.attributs.get(regle.clef)
    objnum = regle.samplers[clef]
    regle.samplers[clef] += 1
#    print ("detecte", objnum, regle.pas,objnum % regle.pas )
    if objnum < regle.vmin:
        return False
    if regle.vmax  and objnum > regle.vmax:
        return False
    if objnum % regle.pas:
        return False
    return True



def printvariable(regle):
    ''' affichage de variables'''
    return regle.stock_param.parms


def f_printvar(regle, _):
    '''#aide||affichage des parametres nommes
       #pattern||;;;printv;C?;=noms?||entree
       #test||redirect||obj||$toto=ok||^;;;printv||end
    '''
#    print("variables:")
    print(printvariable(regle))
    return True


def h_version(regle):
    '''affiche la version'''
    print('pyetl version: ', regle.stock_param.version)
    regle.valide = 'done'




def f_version(*_):
    '''#aide||affiche la version du logiciel et les infos
        #pattern||;;;version;;;
        #test||notest'''
    return True


def f_print(regle, obj):
    '''#aide||affichage d elements de l objet courant
       #pattern1||;C?;L?;print;C?;=noms?||entree
       #pattern2||;;*;print;C?;=noms?||entree
       #test||redirect||obj||^X;ok;;set||^;;X;print||end
    '''
    print(printfunc(regle, obj))
    return True

def f_retour(regle, obj):
    '''#aide||ramene les elements apres l execution
       #pattern||;C?;L?;retour;C?;=noms?
       #test||obj||^;;C1;retour;test ok:;noms||end
    '''
#    print ("f_retour", regle.stock_param.idpyetl, printfunc(regle, obj))
    regle.stock_param.retour.append(printfunc(regle, obj))
#    print ("retour stocke",regle.stock_param.retour)
    return True


def h_bloc(regle):
    '''initialise le compteur de blocs'''
    regle.ebloc = 1


def f_bloc(*_):
    '''#aide||definit un bloc d'instructions qui reagit comme une seule
       #pattern||;;;bloc;;
       #test||obj||^X;1;;set;||C1;B;;;;;;bloc;||^X;A;;set;||C1;B;;;;;;~fin_bloc;||atv;X;1;
    '''

    return True


def h_finbloc(regle):
    '''initialise le compteur de blocs'''
    regle.ebloc = -1


def f_finbloc(*_):
    '''#aide||definit la fin d'un bloc d'instructions
       #pattern||;;;fin_bloc;;
       #test||obj||^X;1;;set;||C1;B;;;;;;~bloc;||^X;A;;set;||C1;B;;;;;;fin_bloc;||atv;X;1;
       '''
    return True


def h_testobj(regle):
    ''' definit la regle comme createur'''
    regle.chargeur = True # c est une regle qui cree des objets
    return True

def f_testobj(regle, obj):
    '''#aide||cree des objets de test pour les tests fonctionnels
       #aide_spec||parametres:liste d'attributs,liste valeurs,nom(niv,classe),nombre
       #pattern||L;LC;;testobj;C;?N||sortie
       #test||rien||^A;1;;testobj;essai;2||cnt;2
    '''
    if not obj.virtuel:
        return False
    return f_creobj(regle, obj)



def f_creobj(regle, obj):
    '''#aide||cree des objets de test pour les tests fonctionnels
       #aide_spec||parametres:liste d'attributs,liste valeurs,nom(niv,classe),nombre
       #pattern||L;LC;?L;creobj;C;?N||sortie
       #test||obj||^A;1;;creobj;essai;2||cnt;3
    '''

    noms = regle.params.att_sortie.liste
    vals = regle.params.val_entree.liste
    tmp = regle.params.cmp1.liste
#    print ('testobj: ',regle.params.cmp1)

    ident = (tmp[0], tmp[1]) if len(tmp) == 2 else ('niv_test', tmp[0])

    if regle.getvar("schema_entree"):
        schema = regle.stock_param.schemas[regle.getvar("schema_entree")]
    else:
        schema = regle.stock_param.init_schema('schema_test', origine='B', stable=False)
    gen_schema = ident not in schema.classes
    schemaclasse = schema.setdefault_classe(ident)
    #TODO gérer les dates
    for nom, val in zip(noms, vals):
        try:
            int(val)
            type_attribut = 'E'
        except (ValueError, TypeError):
            try:
                float(val)
                type_attribut = 'F'
            except (ValueError, TypeError):
                type_attribut = 'T'
        if gen_schema:
            schemaclasse.stocke_attribut(nom, type_attribut=type_attribut)
    nombre = int(regle.params.cmp2.num) if regle.params.cmp2.num is not None else 1
    for i in range(nombre):
        obj2 = Objet(ident[0], ident[1], format_natif='interne')
        obj2.setschema(schemaclasse)
        obj2.attributs.update([j for j in zip(noms, vals)])
#        print ("objet_test",obj2.attributs,obj2.schema.schema.nom)
        obj2.setorig(i)
        try:
            regle.stock_param.moteur.traite_objet(obj2, regle.branchements.brch["next:"])
        except StopIteration as abort:
#            print("intercepte abort",abort.args[0])
            if abort.args[0] == '2':
                break
            raise
    return True


#def h_archive(regle):
#    '''helper d archivage'''
#    dest = os.path.join(regle.getvar('_sortie', regle.params.cmp1.val))
#    print ("preparation archive",regle.params.val_entree.liste,dest)
#
#    os.makedirs(os.path.dirname(dest), exist_ok=True)
#    regle.sortie = dest

def h_ftpupload(regle):
    '''definit la regle comme declenchable'''
    regle.chargeur = True
    codeftp = regle.params.cmp1.val
    serveur = regle.getvar("server_"+codeftp, '')
    servertyp = regle.getvar("ftptyp_"+codeftp, '')
    user = regle.getvar("user_"+codeftp, '')
    passwd = regle.getvar("passwd_"+codeftp, regle.params.cmp2.val)
    regle.setvar('acces_ftp', (codeftp, serveur, servertyp, user, passwd))
    regle.ftp = None


def f_ftpupload(regle, obj):
    '''#aide||charge un fichier sur ftp
  #aide_spec||;nom fichier; (attribut contenant le nom);ftp_upload;ident ftp;
    #pattern||;?C;?A;ftp_upload;C;?C
       #test||notest
    '''
    if not regle.ftp:
        codeftp, serveur, servertyp, user, passwd = regle.getvar('acces_ftp')
#        print ('ouverture acces ',regle.getvar('acces_ftp'))
        if servertyp == "ftp":
            regle.ftp = ftplib.FTP(host=serveur, user=user, passwd=passwd)
        else:
            regle.ftp = ftplib.FTP_TLS(host=serveur, user=user, passwd=passwd)

    filename = obj.attributs.get(regle.params.att_entree.val, regle.params.val_entree.val)
    destname = os.path.basename(filename)
    try:
        localfile = open(filename, 'rb')
        regle.ftp.storbinary("STOR "+destname, localfile)
        localfile.close()
        return True

    except ftplib.error_perm:
        print("!!!!! erreur ftp: acces non autorisé")
        return False




def h_archive(regle):
    '''definit la regle comme declenchable'''
    regle.chargeur = True



def f_archive(regle, obj):
    '''#aide||zippe les fichiers ou les repertoires de sortie
  #aide_spec|| parametres:liste de noms de fichiers(avec *...);attribut contenant le nom;archive;nom
    #pattern||;?C;?A;archive;C;
       #test||notest
       '''
#    if not obj.virtuel:
#        return False
    dest = regle.params.cmp1.val+".zip"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    stock = dict()
    print("archive", regle.params.val_entree.liste, dest, regle.getvar('_sortie'))
    if regle.params.att_entree.val:
        fich = obj.attributs.get(regle.params.att_entree.val)
        if fich:
            stock[fich] = fich
        mode = 'a'
    else:
        mode = 'w'
        for f_interm in regle.params.val_entree.liste:
            clefs = []
            if '*' in os.path.basename(f_interm):
                clefs = [i for i in os.path.basename(f_interm).split('*') if i]
#                print( 'clefs de fichier zip',clefs)
                f_interm = os.path.dirname(f_interm)
            if os.path.isdir(f_interm):
                for fich in os.listdir(f_interm):
#                    print(' test fich ',fich, [i in fich for i in clefs])
                    if all([i in fich for i in clefs]):
                        stock[os.path.join(f_interm, fich)] = fich
            else:
                stock[f_interm] = f_interm

    with zipfile.ZipFile(dest, compression=zipfile.ZIP_BZIP2, mode=mode) as file:
        for i in stock:
            file.write(i, arcname=stock[i])
    return True



def traite_parallelbatch(regle):
    '''traite les batchs en parallele'''
    commande = []
    args = []
    idobj =[]
    mapper = regle.stock_param
    for n, obj in enumerate(regle.store):
        idobj.append(n)
        comm = obj.attributs.get(regle.params.att_entree.val, regle.params.val_entree.val)
        commande.append(comm if comm else obj.attributs.get('commandes'))
        entree = obj.attributs.get('entree', mapper.get_param("_entree"))
        rep_sortie = obj.attributs.get('sortie', mapper.get_param("_sortie"))
        param_attr = obj.attributs.get('parametres') # parametres en format hstore
        if param_attr:
            params_obj = ['='.join(re.split('"=>"', i))
                      for i in re.split('" *, *"', param_attr[1:-1])]
        else:
            params_obj = []
        params = ' '.join(params_obj)
        args.append(entree+' '+rep_sortie+' '+params)
    nprocs = regle.params.cmp1.num
    runpyetl = regle.params.runpyetl
    with ProcessPoolExecutor(max_workers=nprocs) as executor:
        results = {i:res for i, res in zip(idobj, executor.map(runpyetl, commande, args))}
    traite = regle.stock_param.moteur.traite_objet
    for i in sorted(results):
        obj = regle.store[i]
        obj.attributs[regle.params.att_sortie.val] = str(results[i])
        regle.branchements.brch["end:"]
        traite(obj, regle.branchements.brch["end:"])


def h_parallelbatch(regle):
    '''charge la librairie threading sino repasse en mode batch'''
    regle.store = True
    regle.traite_stock = traite_parallelbatch
    regle.nbstock = 0
    regle.traite = 0
    regle.tmpstore = []


def f_parallelbatch(regle, obj):
    '''#aide||execute un traitement batch en processing a partir des parametres de l'objet
  #aide_spec||parametres:attribut_resultat,commandes,attribut_commandes,batch
    #pattern||?A;?C;?A;multiprocess;N
     #schema||ajout_attribut
       #!test||obj;;2||^parametres;"nom"=>"V1", "valeur"=>"1";;set||^X;#obj,#atv;;multiprocess;2||atv;X;1
'''
    regle.tmpstore.append(obj)
    regle.nbstock += 1
    return True


def h_batch(regle):
    '''definit la fonction comme etant a declencher'''
    if regle.params.cmp1.val:
        regle.chargeur = True

def f_batch(regle, obj):
    '''#aide||execute un traitement batch a partir des parametres de l'objet
  #aide_spec||parametres:attribut_resultat,commandes,attribut_commandes,batch
    #pattern||A;?C;?A;batch;?=run;?N||cmp1
     #schema||ajout_attribut
       #test||obj||^parametres;"nom"=>"V1", "valeur"=>"1";;set||^X;#obj,#atv;;batch||atv;X;1
      #test2||obj||^X;#obj,#atv:V1:1;;batch||atv;X;1
    '''
    comm = obj.attributs.get(regle.params.att_entree.val, regle.params.val_entree.val)
    commande = comm if comm else obj.attributs.get('commandes')
#    print("commande batch", commande)
    if not commande:
        return False
    mapper = regle.stock_param
    entree = obj.attributs.get('entree', mapper.get_param("_entree"))
    sortie = obj.attributs.get('sortie', mapper.get_param("_sortie"))
#    chaine_comm = ':'.join([i.strip(" '") for i in commande.strip('[] ').split(',')])
    parametres = obj.attributs.get('parametres') # parametres en format hstore
    params = None
    if parametres:
        params = ['='.join(re.split('"=>"', i))
                  for i in re.split('" *, *"', parametres[1:-1])]

#        params = [re.sub(i.strip('"').replace('"=>"', '=') for i in parametres.split('", "')]

#        return True
#    print('fbatch parametres', commande, parametres, params)

    processor = regle.stock_param.getpyetl(commande, liste_params=params,
                                           entree=entree, rep_sortie=sortie)
    if processor is None:
        return False
#    print('batch :', regle.stock_param.idpyetl, '->', processor.idpyetl,
#          chaine_comm, 'in:', processor.get_param('_entree'),
#          'out:', processor.get_param('_sortie'), 'par:', ' '.join(params))

    lu_total, lu_fichs, nb_total, nb_fichs = processor.process(debug=1)
    obj.attributs["#objets_lus"] = str(lu_total)
    obj.attributs["#fichiers_lus"] = str(lu_fichs)
#    no2, nf2 = processor.menage_final()
    if processor.moteur:
        obj.attributs["#objets_dupliques"] = str(processor.moteur.dupcnt)
    obj.attributs["#objets_lus_db"] = str(processor.dbread)
    obj.attributs["#objets_ecrits"] = str(nb_total)
    obj.attributs["#fichiers_ecrits"] = str(nb_fichs)
    obj.attributs[regle.params.att_sortie.val] = str(processor.retour)
#    print ("retour batch", processor.idpyetl, str(processor.retour))
    return True




def h_statprint(regle):
    ''' imprime les stats a la fin'''
#        print ('impression stats ')
    regle.stock_param.statprint = "print"
    regle.stock_param.statfilter = regle.params.cmp1.val or regle.params.att_sortie.val
    regle.valide = 'done'

def f_statprint(*_):
    '''#aide||affiche les stats a travers une macro eventuelle
    #aide_spec||statprint;macro
       #pattern||;;;statprint;?C;
       #test||notest
    '''
    return True

def h_statprocess(regle):
    ''' retraite les stats en appliquant une macro'''
#    print ('impression stats ')
    regle.stock_param.statprint = "statprocess"
    regle.stock_param.statfilter = regle.params.cmp1.val or regle.params.att_sortie.val
    regle.stock_param.statdest = regle.params.cmp2.val or regle.params.val_entree.val

    regle.valide = 'done'


def f_statprocess(*_):
    '''#aide||retraite les stats en appliquant une macro
    #aide_spec||statprocess;macro de traitement;sortie
       #pattern||;;;statprocess;C;?C;
       #test||obj;;4||$stat_defaut=X||^T;;;stat>;cnt;||^;;;statprocess;#atv:T:4||rien
    '''
    return True



def f_schema_liste_classes(regle, obj):
    '''#aide||cree des objets ou reeels a partir des descriptions de schemas (1 objet par classe)
    #helper||chargeur
    #pattern||;;;liste_schema;C;?=reel
    '''
    schema = regle.stock_params.schemas.get(regle.params.cmp1.val)
    if schema is None:
        return False
    virtuel = True
    if regle.params.cmp2.val:
        virtuel = False
    for i in schema.classes:
        niveau, classe = i
        obj2 = Objet(niveau, classe, format_natif='interne',
                     conversion='virtuel' if virtuel else None,
                     schema=schema.classes[i])
        obj2.initattr()
        try:
            regle.stock_param.moteur.traite_objet(obj2, regle.branchements.brch["next:"])
        except StopIteration as abort:
    #            print("intercepte abort",abort.args[0])
            if abort.args[0] == '2':
                break
            raise
    return True

# cas particulier : declaration de sorties supplementaires :
# a partir du moment ou elles sont declarees par
# la fonction addsortie elles sont automatiquement gerees par l'interpreteur et le compilateur
def h_filter(regle):
    '''prepare les sorties pour le filtre '''

    ls1 = regle.params.cmp1.liste
    ls2 = regle.params.cmp2.liste if regle.params.cmp2.liste else regle.params.cmp1.liste
    regle.liste_sortie = dict(zip(ls1, ls2))
    for i in ls2:
        regle.branchements.addsortie(i+':')
    regle.branchements.addsortie('#autre:')
    regle.branchements.addsortie('#blanc:')
    regle.branchements.addsortie('#vide:')
    return True


def f_filter(regle, obj):
    '''#aide||filtre en fonction d un attribut
    #pattern||?S;?C;A;filter;LC;?LC
       #test||obj||^WW;;C1;filter;A,B,C||+A:;;;;X;1;;~set||+B:;;;;X;2;;~set||atv;X;1
      #test2||obj||^WW;;C1;filter;A,B,C;1,2,3||+1:;;;;X;1;;~set||atv;X;1
    '''
    if regle.params.att_entree.val in obj.attributs:
        valeur = obj.attributs[regle.params.att_entree.val]
    elif regle.params.val_entree.val:
        valeur = regle.params.val_entree.val
    else:
        valeur = None

    if valeur is not None:
        if valeur in regle.liste_sortie:
            obj.redirect = regle.liste_sortie[valeur]
        elif not valeur:
            obj.redirect = "#blanc"
        else:
            obj.redirect = "#autre"
    else:
        obj.redirect = '#vide'

    if regle.fstore:
        regle.fstore(regle.params.att_sortie, obj, obj.redirect)
    obj.redirect = obj.redirect+':'
    return True