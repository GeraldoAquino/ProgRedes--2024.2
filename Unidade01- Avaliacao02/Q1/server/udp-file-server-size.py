import socket

DIRBASE = "files/"
INTERFACE = '127.0.0.1'
PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((INTERFACE, PORT))

print("Servidor escutando em ...", (INTERFACE, PORT))

while True:
    try:
        # Recebe o nome do arquivo
        data, source = sock.recvfrom(4096)
        fileName = data.decode('utf-8')
        
        # Retorna ao estado de escutar novas conexões, após o cliente encerrar a conexão
        if fileName == 'exit':
            print(f"Cliente {source} encerrou a conexão.")
            print("Servidor escutando em ...", (INTERFACE, PORT))
            continue
        
        
        print(f"Recebi pedido para o arquivo {fileName} de {source}")
        caminho = DIRBASE + fileName

        try:
            # Tenta abrir o arquivo para verificar se ele existe 
            with open(caminho, 'rb') as fd:
                # Envia o número 0 para informar que o arquivo existe 
                sock.sendto(b'\x00\x00', source)

                # Obtém o tamanho do arquivo usando tell(), que retorna a posição atual do cursor após ser movido para o final com seek()
                fd.seek(0, 2)  
                tam = fd.tell()
                sock.sendto(tam.to_bytes(8, 'big'), source)
                # Volta ao início do arquivo para começar o envio
                fd.seek(0) 

                print(f"Enviando arquivo {fileName} de {tam} bytes...")
                blocos_enviados = 0
                bloco = fd.read(4096)
                while bloco != b'':
                    sock.sendto(bloco, source)
                    blocos_enviados += len(bloco)
                    print(f"Enviado {blocos_enviados}/{tam} bytes", end="\r")
                    bloco = fd.read(4096)

                print(f"\nArquivo {fileName} enviado com sucesso para {source}.")
        except FileNotFoundError:
            # Envia o número 1 para informar que o arquivo não existe
            sock.sendto(b'\x00\x01', source)
            print(f"Arquivo {fileName} não encontrado.")
    except Exception as e:
        print(f"Erro no servidor: {e}")
