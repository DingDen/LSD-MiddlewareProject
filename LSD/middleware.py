import socket
import threading
import json
import time
import hashlib
import mysql.connector

# CONFIGURAÇÃO E UTILITÁRIOS

class DistributedDBMiddleware:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.id = config['local_node']['id']
        self.host = config['local_node']['ip']
        self.port = config['local_node']['port']
        self.db_config = config['local_node']['db_config']
        self.peers = config['peers'] # Lista de dicionários
        
        self.coordinator_id = max([p['id'] for p in self.peers] + [self.id]) # Inicialmente o maior ID
        self.active = True
        self.connections = {} # Cache de conexões
        
        # Iniciar Servidor Socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        print(f"[*] No {self.id} iniciado em {self.host}:{self.port}", flush=True)
        print(f"[*] Coordenador atual: No {self.coordinator_id}", flush=True)

    # CAMADA DE INTEGRIDADE (CHECKSUM)
    def generate_checksum(self, data):
        return hashlib.md5(json.dumps(data, sort_keys=True).encode('utf-8')).hexdigest()

    def validate_checksum(self, data, received_checksum):
        return self.generate_checksum(data) == received_checksum

    # CAMADA DE BANCO DE DADOS
    def execute_local_query(self, query, params=None):
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            
            if query.strip().upper().startswith("SELECT"):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = {"status": "OK", "rows_affected": cursor.rowcount}
            
            conn.close()
            return result
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}

    # COMUNICAÇÃO P2P (SOCKETS)
    def send_message(self, target_ip, target_port, message_type, payload):
        try:
            message = {
                "origin_id": self.id,
                "type": message_type,
                "payload": payload,
                "timestamp": time.time()
            }
            message["checksum"] = self.generate_checksum(message)
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2) # Timeout curto para detectar falhas
            s.connect((target_ip, target_port))
            s.send(json.dumps(message).encode('utf-8'))
            
            response = s.recv(4096).decode('utf-8')
            s.close()
            return json.loads(response)
        except Exception as e:
            print(f"[!] Falha ao conectar com {target_ip}: {e}")
            return None

    # ALGORITMO DE ELEIÇÃO (BULLY SIMPLIFICADO)
    def start_election(self):
        print("[!] Iniciando Eleição...")
        higher_nodes = [p for p in self.peers if p['id'] > self.id]
        
        if not higher_nodes:
            self.coordinator_id = self.id
            self.broadcast_message("COORDINATOR", {"new_coord": self.id})
            print(f"[*] Eu (Nó {self.id}) sou o novo Coordenador.")
        else:
            # Simplificação: Tenta contatar maiores, se falhar, assume.
            pass

    # PROTOCOLO ACID (TWO-PHASE COMMIT - 2PC)
    def handle_write_request(self, query):
        # Fase 1: Prepare
        print(f"[*] Iniciando 2PC para: {query}")
        votes = []
        for peer in self.peers:
            resp = self.send_message(peer['ip'], peer['port'], "PREPARE", {"query": query})
            if resp and resp.get("vote") == "YES":
                votes.append(True)
            else:
                votes.append(False)
        
        # Fase 2: Commit ou Abort
        if all(votes):
            self.broadcast_message("COMMIT", {"query": query})
            self.execute_local_query(query) # Executa localmente
            return "SUCCESS: Transação replicada em todos os nós."
        else:
            self.broadcast_message("ABORT", {})
            return "ERROR: Transação abortada (Consenso falhou)."

    def broadcast_message(self, msg_type, payload):
        for peer in self.peers:
            self.send_message(peer['ip'], peer['port'], msg_type, payload)

    # PROCESSAMENTO DE MENSAGENS
    def process_request(self, client_socket):
        try:
            data = client_socket.recv(4096).decode('utf-8')
            if not data: return
            
            msg = json.loads(data)
            
            # Verificar Integridade
            if "checksum" in msg:
                payload_check = msg.copy()
                del payload_check['checksum']
                if not self.validate_checksum(payload_check, msg['checksum']):
                    print("[!] Erro de Checksum detectado!")
                    return

            msg_type = msg.get("type")
            payload = msg.get("payload")
            response = {}

            print(f"[*] Recebido {msg_type} de {msg.get('origin_id', 'Cliente')}")

            # Lógica do Servidor
            if msg_type == "CLIENT_QUERY":
                query = payload["query"]
                is_write = not query.strip().upper().startswith("SELECT")
                
                if is_write:
                    if self.id == self.coordinator_id:
                        result_msg = self.handle_write_request(query)
                        response = {"status": "OK", "result": result_msg, "node": self.id}
                    else:
                        # Redirecionar para o coordenador ou rejeitar (aqui vamos rejeitar para simplificar)
                        response = {"status": "REDIRECT", "leader": self.coordinator_id}
                else:
                    # Leitura: Balanceamento de carga (executa local)
                    db_res = self.execute_local_query(query)
                    response = {"status": "OK", "result": db_res, "node": self.id}

            elif msg_type == "PREPARE":
                # Verifica se pode escrever (simulação de lock)
                response = {"vote": "YES"}
            
            elif msg_type == "COMMIT":
                self.execute_local_query(payload["query"])
                response = {"status": "ACK"}

            elif msg_type == "HEARTBEAT":
                response = {"status": "ALIVE"}

            client_socket.send(json.dumps(response).encode('utf-8'))
            client_socket.close()

        except Exception as e:
            print(f"[!] Erro processando requisição: {e}")

    # THREADS DE FUNDO
    def heartbeat_loop(self):
        while self.active:
            time.sleep(5) # A cada 5 segundos
            # Enviar heartbeat para o coordenador ou peers
            # Se coordenador falhar, chamar start_election()
            print("[*] Heartbeat check...")

    def start(self):
        # Iniciar Thread de Heartbeat
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        
        # Loop Principal de Aceite de Conexões
        while True:
            client, addr = self.server_socket.accept()
            threading.Thread(target=self.process_request, args=(client,)).start()

if __name__ == "__main__":
    # Exemplo de uso: python middleware.py config.json
    import sys
    if len(sys.argv) < 2:
        print("Uso: python middleware.py <config_file>")
    else:
        mw = DistributedDBMiddleware(sys.argv[1])
        mw.start()