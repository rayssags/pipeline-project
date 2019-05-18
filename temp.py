# -*- coding: utf-8 -*-
from astropy.io import fits
import astropy
import glob
import os.path
import pandas as pd
import os
from tqdm import tqdm
from itertools import repeat
import numpy as np

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
#if not os.path.isfile(arquivo_auxiliar): #<-------------------------------------------------------------------------- checar essa função
#	df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])	
#	df.to_csv(arquivo_auxiliar, index=False)

df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])	
df.to_csv(arquivo_auxiliar, index=False)



''' Cria o arquivo temporário '''
def agrupar(arquivo_fits, arquivo_auxiliar):
	df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])
	hdu = fits.open(arquivo_fits)
	header = hdu[0].header
	hdu.close()
	df.at[0, 'tipo_imagem'] = header['OBJECT']
	df.at[0, 'filtro'] = 'B'
	df.at[0, 'tempo_exposicao'] = header['EXPTIME']
	df.at[0, 'caminho_arquivo'] = arquivo_fits
	''' Adiciona as informações da imagem ao arquivo '''
	df.to_csv(arquivo_auxiliar, index=False, header=None, mode = 'a')
	return

''' Mapeia as informações de todos os fits originais '''
w = list(map(agrupar, tqdm(arquivos_brutos, ascii=False, desc='Guardando informações dos headers'), repeat(arquivo_auxiliar)))
del w

dimensoes = fits.open(arquivos_brutos[0])[0].data.shape
arquivo_auxiliar_dados = pd.read_csv(arquivo_auxiliar)
print('Criando bias frame')

''' Criando masterbias pela mediana'''
arquivos_bias = arquivo_auxiliar_dados.loc[arquivo_auxiliar_dados['tipo_imagem'] == 'zero', 'caminho_arquivo']
imagens = list(map(lambda x: fits.open(x)[0].data, arquivos_bias))
master_bias_data = np.median(imagens, axis = 0)
master_bias_hdu = fits.PrimaryHDU(master_bias_data)
master_bias_caminho = os.path.join(diretorio_temporario, 'masterbias.fits')
master_bias_hdu.writeto(master_bias_caminho, overwrite=True)

del master_bias_hdu
''' Criando flat pela mediana'''
flats = arquivo_auxiliar_dados.loc[arquivo_auxiliar_dados['tipo_imagem'] == 'flat']
tempos_exposicao_flats = flats['tempo_exposicao'].unique()

def master_flat(tempo_exposicao_flats):
	arquivos = flats.loc[flats['tempo_exposicao'] == tempo_exposicao_flats, 'caminho_arquivo']
	imagens = list(map(lambda x: fits.open(x)[0].data, arquivos))
	master_flat_data = np.median(imagens, axis = 0) - master_bias_data
	master_flat_data_normalizado = master_flat_data/np.mean(master_flat_data)
	master_flat_hdu = fits.PrimaryHDU(master_flat_data_normalizado)
	master_flat_caminho = os.path.join(diretorio_temporario, 'masterflat_norm_{}.fits'.format(tempo_exposicao_flats))
	master_flat_hdu.writeto(master_flat_caminho, overwrite=True)
	del master_flat_hdu

print('Criando flat field normalizado')

w = list(map(master_flat, tempos_exposicao_flats))
del w

#w = list(map(master_flat, tqdm(tempos_exposicao_flats, ascii=False, desc='Criando flat field normalizado:')))
#del w


'''
Agora falta descobrir como corrigir céu
- determinar quais regiões não tem estrelas
- fazer fit nessas regiões
'''