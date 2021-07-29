"""
Módulo com funções para a crição de um pipeline básico de redução de dados
astronômicos em Python. Faz parte da avaliação da disciplina Tratamento de
Dados Astronômicos do curso de Astronomia do Observatório do Valongo
da Universidade Federal do Rio de Janeiro.

Feito por Rayssa Guimarães para Python 3.7.

Pacotes necessários:
os
glob
shutil
itertools
astropy >= 3.1.2
pandas >= 0.24.2
tqdm >= 4.31.1
numpy >= 1.16.2
inquirer >= 2.6.3

Só pode ser executado em terminais interativos
"""

from astropy.io import fits
import astropy
import glob
import os.path
import pandas as pd
import os
from tqdm import tqdm
from itertools import repeat
import numpy as np
import inquirer
import shutil

# ============================= VARIÁVEIS GLOBAIS =============================

diretorio_atual =  os.getcwd()
print('Executando em {}'.format(diretorio_atual))

# verificação da existência de alguns diretórios; caso não existam, são criados
#	diretorio temporário que pode ser deletado ao final da execução
diretorio_temporario = os.path.join(diretorio_atual, 'temp')

def temp_dir():
	try:
		os.mkdir(diretorio_temporario)
		return diretorio_temporario
	except FileExistsError:
		pass
	return

#	diretorio de saida das imagens tratadas
diretorio_output = os.path.join(diretorio_atual, 'output')

def output_dir():
	try:
		os.mkdir(diretorio_output)
	except FileExistsError:
		pass	
	return
# localização do arquivo com a informação dos headers
arquivo_auxiliar = os.path.join(diretorio_temporario, 'informacao_headers.csv')

# localização final do masterbias
master_bias_caminho = os.path.join(diretorio_temporario, 'masterbias.fits')


# ================================== FUNÇÕES ==================================
def agrupar_arquivos(arquivo_fits, arquivo_auxiliar):
	"""Essa função adicona as informações relevantes do header de um arquivo
	fits a um dataframe.

	Args:
	arquivo_fits (str): Arquivo fits que terá as informações adicionadas ao
	arquivo auxiliar.
	arquivo_auxiliar (str): Caminho do dataframe onde as informações ficarão
	salvas.

	Returns:
	arquivo_auxiliar (str) 
	"""

	# inicia um dataframe com colunas das informações a serem coletadas do header do fits
	df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])

	# abre o arquivo fits e coleta o header
	hdu = fits.open(arquivo_fits)
	header = hdu[0].header
	hdu.close()

	# preenche uma linha do daaframe com as informações de interesse do header
	df.at[0, 'tipo_imagem'] = header['OBJECT']
	df.at[0, 'filtro'] = 'B'
	df.at[0, 'tempo_exposicao'] = header['EXPTIME']
	df.at[0, 'caminho_arquivo'] = arquivo_fits

	# anexa essa linha ao arquivo
	df.to_csv(arquivo_auxiliar, index=False, header=None, mode = 'a')
	
	return


def criar_arquivo_auxiliar():
	"""Cria um dataframe com todas as informações relevantes
	dos headers dos arquivos fits dentro de um diretório e as
	adiciona ao arquivo auxiliar.

	Args:
	diretorio_arquivos (str): Caminho para os diretório dos arquivos fits brutos.
	O default é o diretório onde o código está sendo rodado.
	"""

	# verifica a existencia do diretorio temporario
	temp_dir()

	# indicação do diretório onde estão os arquivos
	questions = [inquirer.List('dir',
	message="O diretório de arquivos é o diretório atual?", choices=['Sim', 'Não'])]
	if inquirer.prompt(questions)['dir'] != "Sim":
		diretorio_arquivos = input("Insira o caminho do diretório de arquivos: ")
	else: diretorio_arquivos = './'

	# lista de arquivos fits dentro do diretorio
	arquivos_brutos = glob.glob(diretorio_arquivos + '/*.fits')
	df = pd.DataFrame(columns=['tipo_imagem', 'filtro', 'tempo_exposicao', 'caminho_arquivo'])	
	df.to_csv(arquivo_auxiliar, index=False)

	# colete das informações para todos os arquivos dentro do diretório
	w = list(map(agrupar_arquivos, tqdm(arquivos_brutos, ascii=False, desc='Guardando informações dos headers'), repeat(arquivo_auxiliar)))
	del w
	return

def master_bias():
	"""Essa função cria um master bias com todos os arquivos fits que tem a
	classificação `zero` no arquivo auxiliar
	Esses arquivos são combinados através da mediana."""
	print("--------------------------- Master bias ---------------------------")
	print("Criando o master bias")

	# checa a existência do arquivo auxiliar
	try:
		arquivo_auxiliar_dados = pd.read_csv(arquivo_auxiliar)
	except:
		return print("Arquivo com informações do header não encontrado. Tente a função criar_arquivo_auxiliar antes de tentar novamente.")

	# leitura de todos os arquivos de bias
	arquivos_bias = arquivo_auxiliar_dados.loc[arquivo_auxiliar_dados['tipo_imagem'] == 'zero', 'caminho_arquivo']
	imagens = list(map(lambda x: fits.open(x)[0].data, arquivos_bias))
	
	# combina os arquivos pela mediana
	master_bias_data = np.median(imagens, axis = 0)
	master_bias_hdu = fits.PrimaryHDU(master_bias_data)

	# salva o arquivo combinado
	master_bias_hdu.writeto(master_bias_caminho, overwrite=True)
	del master_bias_hdu
	return 

def master_flat():
	"""Essa função cria um master flat com todos os arquivos fits que tem a
	classificação `flat` no arquivo auxiliar.
	Os arquivos de flat são corrigidos pelo master bias, depois combinados pela
	mediana e por fim são normalizados pela média."""
	print("--------------------------- Master flat ---------------------------")
	# checa a existência do arquivo auxiliar
	try:
		arquivo_auxiliar_dados = pd.read_csv(arquivo_auxiliar)
	except:
		return print("Arquivo com informações do header não encontrado. Tente a função criar_arquivo_auxiliar antes de tentar novamente.")
	
	# checa a existência do arquivo de bias
	try:
		master_bias_data = fits.open(master_bias_caminho)[0].data
	except:
		return print("Master bias não encontrado. Tente a função master_bias antes de tentar novamente.")
	
	# escolhe os arquivos de flat com base no tempo de exposição
	arquivo_auxiliar_dados = pd.read_csv(arquivo_auxiliar)
	flats = arquivo_auxiliar_dados.loc[arquivo_auxiliar_dados['tipo_imagem'] == 'flat']
	questions = [inquirer.List('tempo',
	message="Escolha o tempo de exposição",
	choices=list(flats['tempo_exposicao'].unique()),),]
	answers = inquirer.prompt(questions)
	tempo_exposicao = answers["tempo"]
	arquivos = flats.loc[flats['tempo_exposicao'] == tempo_exposicao, 'caminho_arquivo']
	imagens = list(map(lambda x: fits.open(x)[0].data, arquivos))

	master_flat_data = np.median(list(map(lambda x: x/np.mean(x), tqdm(imagens - master_bias_data, ascii=False, desc='Corrigindo bias, normalizando e combinando pela mediana'))), axis = 0) 
	master_flat_hdu = fits.PrimaryHDU(master_flat_data)	
	print("Salvando o master flat")
	master_flat_caminho = os.path.join(diretorio_temporario, 'masterflat_norm_{}.fits'.format(tempo_exposicao))
	master_flat_hdu.writeto(master_flat_caminho, overwrite=True)	
	del master_flat_hdu



def imagens_ciencia():
	"""Essa função corrige e salva cada uma das imagens de ciência com base
	em tempo de exposição. Essas imagens tem a classificação `XO-2b` no arquivo auxiliar.
	As imagens são subtraídas de bias e divididas pelo flat.
	"""
	print("----------------------- Imagens de ciência ------------------------")
	
	# cria o diretorio de output
	output_dir()
	# checa a existência do arquivo auxiliar
	try:
		arquivo_auxiliar_dados = pd.read_csv(arquivo_auxiliar)
	except:
		return print("Arquivo com informações do header não encontrado. Tente a função criar_arquivo_auxiliar antes de tentar novamente.")

	# escolhe as imagens de ciência com base no tempo de exposição
	arquivo_auxiliar_dados = pd.read_csv(arquivo_auxiliar)
	ciencia_imgs = arquivo_auxiliar_dados.loc[arquivo_auxiliar_dados['tipo_imagem'] == 'XO-2b']
	questions = [inquirer.List('tempo',
	message="Escolha o tempo de exposição",
	choices=list(ciencia_imgs['tempo_exposicao'].unique()),),]
	answers = inquirer.prompt(questions)
	tempo_exposicao = answers["tempo"]

	# checa a existência do arquivo de bias
	try:
		master_bias_data = fits.open(master_bias_caminho)[0].data
	except:
		return print("Master bias não encontrado. Tente a função master_bias antes de tentar novamente.")
	
	# checa a existência do arquivo de flat
	try:
		master_flat_caminho = os.path.join(diretorio_temporario, 'masterflat_norm_{}.fits'.format('5.0'))
		master_flat_data = fits.open(master_flat_caminho)[0].data
	except:
		return print("Master flat não encontrado. Tente a função master_flat antes de tentar novamente.")
	def corrigir_ciencia(caminho):
		imagem = fits.open(caminho)[0].data
		imagem = imagem - master_bias_data
		imagem = imagem/master_flat_data
		ciencia_hdu = fits.PrimaryHDU(imagem)
		caminho_imagem = diretorio_output + '/' + caminho.split('/')[-1].replace('.fits', '_corrigida.fits')
		ciencia_hdu.writeto(caminho_imagem, overwrite=True)	
		del ciencia_hdu
	arquivos = ciencia_imgs.loc[ciencia_imgs['tempo_exposicao'] == tempo_exposicao, 'caminho_arquivo']
	imagens = list(map(corrigir_ciencia, tqdm(arquivos, ascii=False, desc='Corrigindo bias e dividindo pelo flat')))
	del imagens
	return

def limpar():
	"""Essa função deleta o diretório de arquivos temporários."""
	shutil.rmtree(diretorio_temporario)
	
def run_pipeline(manter_temp = False):
	"""Essa função executa um pipeline.
	
	Args:
	manter_temp (bool): Manter arquivos temporários. O default é False.
	"""
	criar_arquivo_auxiliar()
	master_bias()
	master_flat()
	imagens_ciencia()
	if manter_temp == False: limpar()
