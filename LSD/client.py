import sys
import socket
import json

BUFFER_SIZE = 4096

class DDBClient:
    def __init__(self):
        self.ip = None
        self.port = None

    def connect(self):
        print("IP do nó middleware:", flush=True)
        self.ip = sys.stdin.readline().strip()

        print("Porta do nó:", flush=True)
        self.port = int(sys.stdin.readline().strip())



    def send_query(self, query):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))

                message = {
                    "type": "CLIENT_QUERY",
                    "payload": { "query": query }
                }

                s.sendall(json.dumps(message).encode())
                data = s.recv(BUFFER_SIZE)
                response = json.loads(data.decode())

            # REDIRECT automático
            if response.get("status") == "REDIRECT":
                print(f"[!] Redirecionando para coordenador (Nó {response['leader']})")

                # descobrir IP/porta do coordenador
                leader_id = response["leader"]
                leader_ip, leader_port = self.get_leader_address(leader_id)

                self.ip = leader_ip
                self.port = leader_port

                return self.send_query(query)

            self.print_response(response)

        except Exception as e:
            print(f"[ERRO] Falha na comunicação: {e}")

    def print_response(self, response):
        print("\n------------------------------------")

        status = response.get("status")

        if status == "OK":
            print(f"Nó executor: {response.get('node')}")
            print("Resultado:")

            result = response.get("result")

            if isinstance(result, list):
                for row in result:
                    print(row)
            else:
                print(result)

        elif status == "REDIRECT":
            print(f"Redirecionado para o coordenador (Nó {response.get('leader')})")

        else:
            print("Erro na execução da query")
            print("Resposta:", response)

        print("------------------------------------\n")

    def info(self):
        print(f"Nó atual: {self.ip}:{self.port}")
    
    def get_leader_address(self, leader_id):
        # Adaptar na hora (colocar ip de cada maquina)
        nodes = {
            1: ("192.168.0.127", 5000),
            2: ("192.168.0.127", 5001),
            3: ("192.168.0.127", 5002),
        }
        return nodes[leader_id]

def main():
    client = DDBClient()
    client.connect()

    print("\n====================================")
    print(" CLIENTE - BANCO DE DADOS DISTRIBUÍDO")
    print("====================================")
    print("Comandos:")
    print("  :node  -> trocar nó")
    print("  :info  -> info do nó atual")
    print("  :exit  -> sair\n")

    while True:
        cmd = input("> ").strip()

        if not cmd:
            continue

        if cmd == ":exit":
            print("Encerrando cliente.")
            break

        elif cmd == ":node":
            client.connect()

        elif cmd == ":info":
            client.info()

        else:
            client.send_query(cmd)

if __name__ == "__main__":
    main()