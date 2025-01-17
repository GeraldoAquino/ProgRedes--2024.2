import socket
import os
import glob
import hashlib

DIRBASE = "server/files/"
SERVER = '127.0.0.1'
PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((SERVER, PORT))
sock.listen(5)

print('Servidor ouvindo conexões...\n')

while True:
    try:
        connection, source = sock.accept()
        print(f"Conexão estabelecida com {source}.\n")

        while True:
            try:
                request = connection.recv(4096).decode('utf-8')
                if not request:
                    break

                if request.lower() == "list":
                    print(f"Cliente {source} solicitou listagem de arquivos.")
                    
                    try:
                        # Listar arquivos no diretório
                        arquivos = os.listdir(DIRBASE)
                        lista_resposta = []

                        for arquivo in arquivos:
                            caminho = os.path.join(DIRBASE, arquivo)
                            if os.path.isfile(caminho):
                                tamanho = os.path.getsize(caminho)
                                lista_resposta.append(f"{arquivo} - {tamanho} bytes")

                        if lista_resposta:
                            resposta = "\n".join(lista_resposta)
                        else:
                            resposta = "Nenhum arquivo encontrado no servidor."

                        # Enviar a lista para o cliente
                        connection.send(resposta.encode('utf-8'))
                        print(f"Listagem enviada para {source}.")
                    except Exception as e:
                        erro = f"Erro ao listar arquivos: {e}"
                        connection.send(erro.encode('utf-8'))
                        print(erro)

                elif request.lower() == "sget":
                    # Recebe o nome do arquivo solicitado pelo cliente
                    fileName = connection.recv(1024).decode('utf-8')
                    print(f"Cliente {source} solicitou o download do arquivo {fileName}.")

                    caminho = os.path.join(DIRBASE, fileName)

                    # Verificação de segurança para garantir que o caminho está dentro da pasta permitida
                    if not os.path.realpath(caminho).startswith(os.path.realpath(DIRBASE)):
                        connection.send("Erro: Tentativa de acesso a diretório inválido.")
                        print(f"Cliente {source} tentou acessar um arquivo fora da pasta permitida.")
                        continue

                    try:
                        # Verifica se o arquivo existe
                        if os.path.exists(caminho):
                            # Envia o código 0 para indicar que o arquivo existe
                            connection.send(b'\x00\x00')

                            # Obtém o tamanho do arquivo
                            tam = os.path.getsize(caminho)
                            connection.send(tam.to_bytes(8, 'big'))

                            # Envia o arquivo em blocos de 4096 bytes
                            with open(caminho, 'rb') as fd:
                                print(f"Enviando arquivo {fileName} de {tam} bytes...")
                                blocos_enviados = 0
                                while True:
                                    bloco = fd.read(4096)
                                    if not bloco:
                                        break
                                    connection.send(bloco)
                                    blocos_enviados += len(bloco)
                                    print(f"Enviado {blocos_enviados}/{tam} bytes", end="\r")

                                print(f"\nArquivo {fileName} enviado com sucesso para {source}.\n")
                        else:
                            # Envia o código 1 para indicar que o arquivo não foi encontrado
                            connection.send(b'\x00\x01')
                            print(f"Arquivo {fileName} não encontrado.\n")
                    except Exception as e:
                        erro = f"Erro ao enviar arquivo {fileName}: {e}"
                        connection.send(erro.encode('utf-8'))
                        print(erro)

                elif request.lower() == "mget":
                    # Receber a máscara de arquivos
                    mask = connection.recv(4096).decode('utf-8')
                    print(f"Cliente {source} solicitou arquivos com máscara: {mask}")

                    # Obter lista de arquivos que atendem à máscara
                    arquivos = glob.glob(os.path.join(DIRBASE, mask))
                    arquivos = [os.path.basename(arquivo) for arquivo in arquivos]

                    # Enviar a lista de arquivos encontrados
                    if arquivos:
                        connection.send("\n".join(arquivos).encode('utf-8'))
                    else:
                        connection.send(b"Nenhum arquivo encontrado.")
                        continue

                    # Enviar cada arquivo solicitado
                    for arquivo in arquivos:
                        resposta = connection.recv(1)
                        if resposta == b'\x01':  # Cliente confirmou download
                            caminho = os.path.join(DIRBASE, arquivo)

                            # Verificação de segurança
                            if not os.path.realpath(caminho).startswith(os.path.realpath(DIRBASE)):
                                connection.send("Erro: Tentativa de acesso a diretório inválido.")
                                print(f"Cliente {source} tentou acessar um arquivo fora da pasta permitida.")
                                continue

                            try:
                                with open(caminho, 'rb') as fd:
                                    # Enviar o tamanho do arquivo
                                    fd.seek(0, 2)
                                    tam = fd.tell()
                                    connection.send(tam.to_bytes(8, 'big'))

                                    # Voltar ao início e enviar o conteúdo
                                    fd.seek(0)
                                    while True:
                                        bloco = fd.read(4096)
                                        if not bloco:
                                            break
                                        connection.send(bloco)
                            except FileNotFoundError:
                                print(f"Arquivo {arquivo} não encontrado.")
                                connection.send(b'\x00\x01')  # Erro

                # Verifica se o pedido é um hash, então calcula o hash de um arquivo
                elif request.lower() == "hash":
                    # Recebe o nome do arquivo e o número de bytes do cliente
                    fileName = connection.recv(4096).decode('utf-8')
                    numBytes = connection.recv(4096).decode('utf-8')
            
                    filePath = DIRBASE + fileName
                    # Verifica se o arquivo existe
                    if not os.path.isfile(filePath):
                        connection.send("Erro: Arquivo não encontrado.".encode('utf-8'))
                        continue

                    # Verifica se o valor é inválido
                    numBytes = int(numBytes)
                    if numBytes <= 0:
                        erro = "Erro: Quantidade de bytes tem que ser maior que 0.".encode('utf-8')
                        connection.send(erro)
                        continue

                    tam = os.path.getsize(filePath)
                    # Verifica se o arquivo tem bytes suficientes
                    if numBytes > tam:
                        erro = f"Erro: O arquivo possui apenas {tam} bytes.".encode('utf-8')
                        connection.send(erro)
                        continue

                    try:
                        # Calcula o hash
                        with open(filePath, 'rb') as fd:
                            data = fd.read(numBytes)
                            hashBytes = hashlib.sha1(data).hexdigest()
                            msg = "Hash:".encode('utf-8')
                            msgOF = msg + str(hashBytes).encode()
                            connection.send(msgOF)
                    except Exception as e:
                        erro = f"Erro ao calcular o hash: {e}".encode('utf-8')
                        connection.send(erro)

                elif request.lower() == "cget":
                    try:
                        fileName = connection.recv(4096).decode('utf-8')
                        clientSize = int(connection.recv(4096).decode('utf-8'))
                        clientHash = connection.recv(4096).decode('utf-8')

                        filePath = os.path.join(DIRBASE, fileName)

                        # Verificação de segurança
                        if not os.path.realpath(filePath).startswith(os.path.realpath(DIRBASE)):
                            connection.send("Erro: Tentativa de acesso a diretório inválido.".encode('utf-8'))
                            print(f"Cliente {source} tentou acessar um arquivo fora da pasta permitida.")
                            continue

                        if not os.path.exists(filePath):
                            connection.send("FILE NOT FOUND".encode('utf-8'))
                            continue

                        # Verifica se o hash corresponde
                        if clientSize > 0:
                            with open(filePath, 'rb') as file:
                                data = file.read(clientSize)
                                serverHash = hashlib.sha1(data).hexdigest()

                            if serverHash != clientHash:
                                connection.send("HASH MISMATCH".encode('utf-8'))
                                continue

                        # Se o hash for válido ou o arquivo for novo
                        totalSize = os.path.getsize(filePath)
                        connection.send(f"HASH OK:{totalSize}".encode('utf-8'))

                        # Inicia o envio dos bytes restantes
                        with open(filePath, 'rb') as file:
                            file.seek(clientSize)
                            bytesToSend = totalSize - clientSize

                            while bytesToSend > 0:
                                chunk = file.read(min(4096, bytesToSend))
                                if not chunk:
                                    break
                                connection.send(chunk)
                                bytesToSend -= len(chunk)

                        print(f"Arquivo {fileName} enviado parcialmente com sucesso para {source}.")

                    except Exception as e:
                        erro = f"Erro na funcionalidade cget: {e}"
                        connection.send(erro.encode('utf-8'))
                        print(erro)


            except Exception as e:
                        print(f"Erro: {e}")
                        connection.send(f"Erro: {e}".encode('utf-8'))
        connection.close()
        print(f"Conexão com {source} encerrada.\n")
    except Exception as e:
        print(f"Erro no servidor: {e}")
