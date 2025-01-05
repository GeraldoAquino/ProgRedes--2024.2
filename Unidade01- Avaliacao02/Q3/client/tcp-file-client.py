import socket
import os
import hashlib

DIRBASE = "client/files/"
SERVER = '127.0.0.1'
PORT = 12345

# Criação da pasta 'files' se não existir
os.makedirs(DIRBASE, exist_ok=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((SERVER, PORT))
print('Conectado ao servidor!\n')

# Função de segurança para garantir que o arquivo está dentro da pasta 'files'
def caminhoCerto(arquivoSolicitado):
    # Obtém o caminho real do arquivo solicitado
    real_path = os.path.realpath(os.path.join(DIRBASE, arquivoSolicitado))
    
    # Verifica se o arquivo está dentro da pasta 'files'
    if not real_path.startswith(os.path.realpath(DIRBASE)):
        return None  # Se o arquivo estiver fora da pasta files, retorna None
    
    return real_path  # Retorna o caminho seguro se estiver dentro da pasta 'files'

continuar = True
while continuar:
    print("+--------------------------------------------------------+")
    print("| 1 - Obter a listagem dos arquivos no servidor          |")
    print("+--------------------------------------------------------+")
    print("| 2 - Download de arquivo                                |")
    print("+--------------------------------------------------------+")
    print("| 3 - Download de múltiplos arquivos atravez da mascara  |")
    print("+--------------------------------------------------------+")
    print("| 4 - Calcular o hash de um arquivo                      |")
    print("+--------------------------------------------------------+")
    print("| 5 - Continuar download a partir do hash                |")
    print("+--------------------------------------------------------+")
    print("| 6 - Sair                                               |")
    print("+--------------------------------------------------------+")
    opcao = input("|Escolha uma opção: ")

    if opcao == "1":
        comando = "list"
        sock.send(comando.encode('utf-8'))

        resposta = sock.recv(4096).decode('utf-8')
        print("\nArquivos no servidor:")
        print(resposta)

    elif opcao == "2":
        comando = "sget"
        sock.send(comando.encode('utf-8'))

        nome_arquivo = input("\nDigite o nome do arquivo para download: ")

        # Verifica se o arquivo está dentro da pasta 'files' usando a função segura
        caminho_arquivo = caminhoCerto(nome_arquivo)
        if caminho_arquivo is None:
            print("Erro: O arquivo solicitado está fora da pasta 'files'.")
            continue

        if os.path.exists(caminho_arquivo):
            sobrescrever = input(f"O arquivo {nome_arquivo} já existe. Deseja sobrescrever? (s/n): ").lower()
            if sobrescrever != 's':
                print("Operação cancelada.")
                continue

        sock.send(nome_arquivo.encode('utf-8'))

        resposta = sock.recv(2)
        fileIsOk = int.from_bytes(resposta, 'big')

        if fileIsOk == 0:
            tamDados = sock.recv(8)
            tam = int.from_bytes(tamDados, 'big')
            print(f"Tamanho do arquivo: {tam} bytes")

            with open(caminho_arquivo, 'wb') as fd:
                blocos_recebidos = 0
                while blocos_recebidos < tam:
                    bloco = sock.recv(4096)
                    fd.write(bloco)
                    blocos_recebidos += len(bloco)
                    print(f"Recebido {blocos_recebidos}/{tam} bytes", end="\r")

            print(f"\nArquivo {nome_arquivo} recebido e salvo com sucesso.")
        else:
            print(f"Arquivo {nome_arquivo} não encontrado no servidor.")

    elif opcao == "3":
        comando = "mget"
        sock.send(comando.encode('utf-8'))

        mascara = input("\nDigite a máscara de arquivos (exemplo: *.jpg): ")
        sock.send(mascara.encode('utf-8'))

        arquivos = sock.recv(4096).decode('utf-8')
        if arquivos == "Nenhum arquivo encontrado.":
            print("\nNenhum arquivo encontrado no servidor.")
            continue

        print(f"\nArquivos encontrados: {arquivos}\n")
        arquivos_list = arquivos.split("\n")

        for arquivo in arquivos_list:
            if not arquivo.strip():
                continue

            # Verifica se o arquivo está dentro da pasta 'files' usando a função segura
            caminho_arquivo = caminhoCerto(arquivo.strip())
            if caminho_arquivo is None:
                print(f"Erro: O arquivo {arquivo} está fora da pasta 'files'.")
                continue

            if os.path.exists(caminho_arquivo):
                sobrescrever = input(f"O arquivo {arquivo} já existe. Deseja sobrescrever? (s/n): ").lower()
                if sobrescrever != 's':
                    print(f"Arquivo {arquivo} não será sobrescrito.")
                    continue

            sock.send(b'\x01')

            tamDados = sock.recv(8)
            tam = int.from_bytes(tamDados, 'big')
            print(f"Baixando {arquivo} ({tam} bytes)...")

            with open(caminho_arquivo, 'wb') as fd:
                blocos_recebidos = 0
                while blocos_recebidos < tam:
                    bloco = sock.recv(4096)
                    fd.write(bloco)
                    blocos_recebidos += len(bloco)
                    print(f"Recebido {blocos_recebidos}/{tam} bytes", end="\r")

            print(f"\nArquivo {arquivo} salvo com sucesso.")

    elif opcao == "4":
        sock.send("hash".encode('utf-8'))

        fileName = input("\nDigite o nome do arquivo: ")
        sock.send(fileName.encode('utf-8'))

        numBytes = input("Digite o número de bytes para o hash: ")
        sock.send(numBytes.encode('utf-8'))

        resposta = sock.recv(4096).decode('utf-8')
        print(resposta)

    elif opcao == "5":
        sock.send("cget".encode('utf-8'))
        fileName = input("\nDigite o nome do arquivo: ")

        # Verifica se o arquivo está dentro da pasta 'files' usando a função segura
        localFilePath = caminhoCerto(fileName)
        if localFilePath is None:
            print("Erro: O arquivo solicitado está fora da pasta 'files'.")
            continue

        if not os.path.exists(localFilePath):
            print("Arquivo local não encontrado para continuar o download.")
            continue

        localSize = os.path.getsize(localFilePath)
        sock.send(fileName.encode('utf-8'))
        sock.send(str(localSize).encode('utf-8'))

        with open(localFilePath, 'rb') as file:
            data = file.read(localSize)
            localHash = hashlib.sha1(data).hexdigest()
            sock.send(localHash.encode('utf-8'))

        # Aqui vamos tentar receber uma resposta binária e verificar a resposta do servidor
        serverResponse = sock.recv(4096)

        if serverResponse.decode('utf-8', errors='ignore') == "HASH OK":
            # Recebe o tamanho total do arquivo
            totalSizeData = sock.recv(8)
            totalSize = int.from_bytes(totalSizeData, 'big')

            # Calcula os bytes restantes
            bytesToReceive = totalSize - localSize
            print(f"Tamanho total do arquivo: {totalSize} bytes.")
            print(f"Baixando os últimos {bytesToReceive} bytes...")

            with open(localFilePath, 'ab') as file:
                blocos_recebidos = 0
                while blocos_recebidos < bytesToReceive:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    file.write(chunk)
                    blocos_recebidos += len(chunk)
                    print(f"Recebido {localSize + blocos_recebidos}/{totalSize} bytes", end="\r")

            print("\nDownload continuado com sucesso!")
        else:
            print("\nErro: Hash não corresponde. Verifique o arquivo local.")

    elif opcao == "6":
        break

    else:
        print("Opção inválida. Tente novamente.")

    continuar = input("\nDeseja fazer outra operação? (s/n): ").lower() == 's'

sock.close()
print("\nConexão encerrada.")
