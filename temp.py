# -*- coding: utf-8 -*-
#from astropy.io.fits import fits
import astropy
import glob
import os.path
import pandas as pd
import os


''' Variáveis locais do pipeline '''

diretorio_script = os.path.dirname(__file__)
#diretorio_script =  os.getcwd()
diretorio_temporario = os.path.join(diretorio_script, 'temp')
diretorio_arquivos = os.path.join(diretorio_script, 'data')


arquivos_brutos = glob.glob(diretorio_arquivos + '/*.fits')

arquivo_auxiliar_nome = 'Arquivos_auxiliares.csv'
arquivo_auxiliar = os.path.join(diretorio_temporario, arquivo_auxiliar_nome)


'''

Checa a existência do arquivo auxiliar, caso não exista, ele é criado 
Se o arquivo já existe ele é sobreescrito a fim de evitar duplicatas nas linhas

'''
if not os.path.isfile(arquivo_auxiliar): #<-------------------------------------------------------------------------- checar essa função
	df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])	
	df.to_csv(arquivo_auxiliar, index=False, header=None, mode = 'a')

''' Cria o arquivo temporário '''
def agrupar(aquivo_fits):
	df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])
	hdu = astropy.io.fits.open(arquivo_fits)
	header = hdu[0].header
	hdu.close()
	df.at[0, 'tipo_imagem'] = header['OBJECT']
	df.at[0, 'filtro'] = 'B'
	df.at[0, 'tempo_exposicao'] = header['EXPTIME']
	df.at[0, 'caminho_arquivo'] = arquivo_fits
	''' Adiciona as informações da imagem ao arquivo '''
	df.to_csv(arquivo_auxiliar, index=False, header=None, mode = 'a')

''' Mapeia as informações de todos os fits originais '''
map(agrupar, arquivos_brutos)

