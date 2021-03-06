# -*- coding: utf-8 -*-
"""
Created on Tue Mar 20 20:54:48 2018

@author: claude

module crypt : gere le cryptage des mots de passe dans les parametres de site

"""
import base64
import itertools
import random
import subprocess

CRYPTOCLASS = None






class Crypter(object):
    """classe de gestion de cryptage la classe de base ne crypte rien"""

    def __init__(self, key):
        self.key = key
        self.ext = False

    def setkey(self, key):
        """positionne la clef"""
        self.key = key

#    def crypt(self, val):
#        """crypte une valeur"""
#        return val
#
#    def decrypt(self, val):
#        """decrypte une valeur"""
#        return val

class BasicCrypter(Crypter):
    """cryptage basique un simple XOR avec le mot de passe"""
    def crypt(self, val):
        '''crypte vaguement un mot de passe'''
        crypted = base64.b32encode(bytes(itertools.chain.from_iterable(zip((ord(x)^ord(y)\
              for x, y in zip(val, itertools.cycle(self.key)
                             )), (random.randint(0, 255) for i in range(len(val)))))))
        return ''.join(chr(i) for i in crypted)

    def decrypt(self, val):
        """la decrypte de nouveau"""
        return ''.join([chr(x^ord(y))
                        for x, y in zip(base64.b32decode(val)[::2], itertools.cycle(self.key))])





class ExtCrypter(Crypter):
    """cryptage en utilisant un programme externe"""
    def __init__(self, key):
        super().__init__(key)
        self.ext = True
        self.chelper = None

    def set_ext(self, chelper):
        """positionne le programme"""
        self.chelper = chelper


    def crypt(self, val):
        '''crypte un champ avec un crypteur externe'''
        if self.chelper:
            code = self.chelper + ' d ' + val +' '+ self.key
            fini = subprocess.run(code, stdout=subprocess.PIPE)
            return str(fini.stdout)

    def decrypt(self, val):
        '''decrypte un champ avec un crypteur externe'''

        if self.chelper:
            code = self.chelper + ' d ' + val +' '+self.key
            fini = subprocess.run(code, stdout=subprocess.PIPE)
            return str(fini.stdout)


class HcubeCrypter(Crypter):
    '''module de cryptage par transposition d'hypercube'''
    def __init__(self, key):
        super().__init__(key)
        self.hcube = dict()
        self.rcube = dict()
        self.transposer = list(itertools.permutations(range(4), 4))
        if key:
            self.setkey(key)


    def setkey(self, key):
        '''initialisation de l'hypercube'''

        self.key = key
        inp, pos1, pos2, pos3, pos4 = 0, 0, 0, 0, 0
        propage = lambda x, y: (0, y+1) if x == 4 else (x, y)
        for i in itertools.cycle(key.encode("utf-8")):
            inp = (107+inp+i) % 256
            if inp in self.hcube:
                continue
            self.hcube[inp] = (pos1, pos2, pos3, pos4)
            pos1, pos2 = propage(pos1+1, pos2)
            pos2, pos3 = propage(pos2, pos3)
            pos3, pos4 = propage(pos3, pos4)
            if pos4 == 4:
                break
        self.rcube = {self.hcube[i]:i for i in self.hcube}


    def transcrypt(self, bloc, clef=0):
        '''transposeur'''
        hyc = list(self.hcube[i] for i in bloc)
        thc = (tuple(j[i] for j in hyc) for i in self.transposer[clef])
#        print (" tc",list(tc))
        tpbloc = bytes(self.rcube[i] for i in thc)
#        print (" tc",clef,self.transposer[clef],bloc,tpbloc)
        return tpbloc

    def backcrypt(self, bloc, clef=0):
        '''transposeur inverse'''
        hc1 = list(self.hcube[i] for i in bloc)
        hyc = list([1]*4)
        for i, j in enumerate(self.transposer[clef]):
            hyc[j] = hc1[i]
        thc = (tuple(hcr[i] for hcr in hyc) for i in range(4))
        tpbloc = bytes(self.rcube[i] for i in thc)
        return tpbloc


    def crypt(self, val):
        '''cryptage : le texte a crypter est decompse en modules de 3 lettres
                      auquel on ajoute une lettre aleatoire
                      ce qui donne les blocs de 4 en entree du transposeur
                      le resultat est encode en base 64'''

        binlist = bytes([i for i in val.encode("utf-8")])
        taille = len(binlist)
        pl1 = taille // 256
        pl2 = taille % 256
        flist = bytes([pl1, pl2])+binlist+bytes([random.randint(0, 255) for i in range(3)])
#        print ("flist",flist,len(flist),"xxx",list(range(0,len(flist)-3,3)))
        retour = bytes()
        clef = 0
        for i in range(0, len(flist)-3, 3):
            bloc = flist[i:i+3]+bytes([random.randint(0, 255)])
            bloc_crypt = self.transcrypt(bloc, clef=clef)
            clef = sum(bloc)%24
#            print(" crypt2", bloc,"->",bloc_crypt,"<-")
            retour = retour+bloc_crypt
        crypted = base64.b32encode(bytes(retour))
        return ''.join(chr(i) for i in crypted)

    def decrypt(self, val):
        """decryptage"""
        if not val:
            return ''
        crypted = base64.b32decode(val)
        retour = bytes()
        clef = 0
        for i in range(0, len(crypted)-3, 4):
            bloc_crypt = crypted[i:i+4]
            bloc = self.backcrypt(bloc_crypt, clef=clef)
            retour = retour+bloc[0:3]
            clef = sum(bloc)%24
#            clef=0
#        print ("retour", code, retour)
        taille = retour[0]*256+retour[1]
        if abs(len(retour)-taille) > 5:
#            print ('clef invalide ', len(retour) - taille)
            return val
        textbuf = bytes(retour[2:taille+2])
        try:
            return textbuf.decode("utf-8")
        except UnicodeDecodeError:
            print('clef invalide ')
            return val


CRYPTOLEVELS = {0:Crypter, 1:BasicCrypter, 2:HcubeCrypter, 3:ExtCrypter}
CRYPTOCLASS = [None]

def cryptinit(mapper, key, level):
    """initialise la fonction de cryptage"""
#    print ('initialisation cryptage demande',level,key, key.endswith('='), key[-1])

    if not key:
        key = mapper.get_param("defaultkey")
    if key.endswith('='):
        key = base64.b32decode(key).decode('utf-8')

    if level is None:
        level = mapper.get_param('cryptolevel', 2)
    cclass = CRYPTOLEVELS[level](key)
    if cclass.ext:
        if mapper and mapper.get_param('cryptohelper'):
            chelper = mapper.get_param('cryptohelper')
            cclass.set_ext(chelper)
        else:
            print('cryptohelper non defini ,passage en niveau', level-1)
            cryptinit(mapper, key, level-1)
            return
    CRYPTOCLASS[0] = cclass
#    print ('initialisation cryptage niveau',level,key)


def decrypt(mapper, val, key=None, level=None):
    '''decrypte les mots de passe'''
    if CRYPTOCLASS[0] is None:
        cryptinit(mapper, key, level)
#    print 'decryptage', cryptoclass[0].key, cryptoclass[0].level
    return CRYPTOCLASS[0].decrypt(val)

def crypter(mapper, val, key=None, level=None):
    '''decrypte les mots de passe'''
#    print ('dans cryptage ',val,key,level)
    if CRYPTOCLASS[0] is None:
        cryptinit(mapper, key, level)
    return CRYPTOCLASS[0].crypt(val)



if __name__ == "__main__":
    print(" cryptotest")
    for ii in CRYPTOLEVELS:
        print('test niveau', ii)
        cryptinit(None, 'mot de passe', ii)
        valeur = "test de texte aa bbb cccc ddddddd c"
        print("valeur ", valeur)
        crypte = crypter(None, valeur)
        print("cryptee", crypte)
        decrypte = decrypt(None, crypte)
        if decrypte == valeur:
            res = '------test ok'
        else:
            res = 'erreur cryptage niveau-------------------->'+str(ii)
        print("decrypt", decrypte, res)
