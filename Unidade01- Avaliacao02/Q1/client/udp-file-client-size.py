import socket
DIRBASE = "files/"
SERVER = '127.0.0.1'
PORT = 12345


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    fileName = input("Digite o nome do arquivo: ")
    sock.sendto(fileName.encode('utf-8'), (SERVER, PORT))

    try:
        # Recebe a resposta do servidor sobre a disponibilidade do arquivo
        resposta, _ = sock.recvfrom(2)
        fileIsOk = int.from_bytes(resposta, 'big')

        if fileIsOk == 0:
            # Recebe o tamanho do arquivo
            tamDados, _  = sock.recvfrom(8)
            tam = int.from_bytes(tamDados, 'big')
            print(f"Tamanho do arquivo: {tam} bytes")

            #Grava o arquivo
            with open(DIRBASE + fileName, 'wb') as fd:
                blocos_recebidos = 0
                while blocos_recebidos < tam:
                    bloco, _  = sock.recvfrom(4096)
                    fd.write(bloco)
                    blocos_recebidos += len(bloco)
                    print(f"Recebido {blocos_recebidos}/{tam} bytes", end="\r")

            print(f"\nArquivo {fileName} recebido e salvo com sucesso.")
        else:
            print("Arquivo não encontrado no servidor.")
    except socket.error as e:
        print(f"Erro de conexão: {e}")
    
    # Pergunta ao usuário se deseja continuar solicitando arquivos
    continuar = input("Deseja solicitar outro arquivo? (s/n): ").lower()
    if continuar != 's':
        break

sock.close()
print("Conexão encerrada.")
