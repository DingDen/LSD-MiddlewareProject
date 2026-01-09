# LSD – Middleware de Banco de Dados Distribuído

## Visão Geral

Este projeto implementa um **middleware de banco de dados distribuído**, responsável por intermediar a comunicação entre clientes e múltiplos nós de banco de dados MySQL. O sistema foi desenvolvido com foco em **consistência, coordenação e tolerância básica a falhas**, utilizando conceitos clássicos de sistemas distribuídos.

O middleware permite:

* Execução de **consultas de leitura** em qualquer nó
* Execução de **operações de escrita** de forma coordenada
* **Replicação de dados** entre os nós
* Eleição de um **nó coordenador**

O projeto foi testado localmente, mas foi concebido para funcionar em **múltiplas máquinas** em rede.

---

## Arquitetura do Sistema

A arquitetura é composta por três elementos principais:

* **Cliente (`client.py`)**
  Interface de linha de comando que permite ao usuário enviar consultas SQL para o sistema distribuído.

* **Middleware (`middleware.py`)**
  Cada nó executa uma instância do middleware, que:

  * Escuta conexões via socket
  * Processa requisições de clientes e de outros nós
  * Executa consultas no banco de dados local
  * Coordena operações de escrita

* **Banco de Dados (MySQL)**
  Cada nó possui sua própria instância MySQL, contendo o mesmo schema.

### Coordenação

* O sistema utiliza uma **eleição simplificada baseada no maior ID** para definir o coordenador.
* Apenas o coordenador pode autorizar operações de escrita.
* Leituras podem ser atendidas por qualquer nó.

### Consistência

* Operações de escrita utilizam um **Two-Phase Commit (2PC)** simplificado para garantir consistência entre os nós.

---

## Tecnologias Utilizadas

* Python 3
* Sockets TCP
* Threads
* MySQL 8.x
* Biblioteca `mysql-connector-python`
* JSON para troca de mensagens

---

## Pré-requisitos

Antes de executar o sistema, certifique-se de que cada máquina (ou instância local) possui:

* Python 3 instalado
* MySQL Server instalado e em execução
* Biblioteca Python do MySQL:

```bash
pip install mysql-connector-python
```

---

## Inicialização do Banco de Dados

Recomenda-se utilizar um **script SQL** para padronizar a criação do banco de dados.

### Script `init_db.sql`

```sql
CREATE DATABASE IF NOT EXISTS dist_db;
USE dist_db;

CREATE TABLE IF NOT EXISTS teste (
    id INT PRIMARY KEY
);
```

Execute este script **em cada instância MySQL**, uma vez, antes de iniciar os nós do middleware.

---

## Configuração dos Nós (3 Máquinas)

Cada máquina deve possuir **seu próprio arquivo `config.json`**, apontando para o IP real da máquina na rede.

### Exemplo – Máquina 1 (Nó 1)

```json
{
  "local_node": {
    "id": 1,
    "ip": "192.168.0.10",
    "port": 5000,
    "db_config": {
      "user": "root",
      "password": "password",
      "host": "localhost",
      "database": "dist_db"
    }
  },
  "peers": [
    {"id": 2, "ip": "192.168.0.11", "port": 5000},
    {"id": 3, "ip": "192.168.0.12", "port": 5000}
  ]
}
```

### Exemplo – Máquina 2 (Nó 2)

```json
{
  "local_node": {
    "id": 2,
    "ip": "192.168.0.11",
    "port": 5000,
    "db_config": {
      "user": "root",
      "password": "password",
      "host": "localhost",
      "database": "dist_db"
    }
  },
  "peers": [
    {"id": 1, "ip": "192.168.0.10", "port": 5000},
    {"id": 3, "ip": "192.168.0.12", "port": 5000}
  ]
}
```

### Exemplo – Máquina 3 (Nó 3)

```json
{
  "local_node": {
    "id": 3,
    "ip": "192.168.0.12",
    "port": 5000,
    "db_config": {
      "user": "root",
      "password": "password",
      "host": "localhost",
      "database": "dist_db"
    }
  },
  "peers": [
    {"id": 1, "ip": "192.168.0.10", "port": 5000},
    {"id": 2, "ip": "192.168.0.11", "port": 5000}
  ]
}
```

⚠️ **Importante**:

* Cada nó deve ter um **ID único**
* O campo `ip` deve ser o IP real da máquina
* O MySQL roda localmente (`localhost`) em cada máquina

---

Cada nó utiliza um arquivo `config.json`. Abaixo está um exemplo para um nó local:

```json
{
  "local_node": {
    "id": 1,
    "ip": "192.168.0.127",
    "port": 5000,
    "db_config": {
      "user": "root",
      "password": "password",
      "host": "localhost",
      "database": "dist_db"
    }
  },
  "peers": [
    {"id": 2, "ip": "192.168.0.127", "port": 5001},
    {"id": 3, "ip": "192.168.0.127", "port": 5002}
  ]
}
```

⚠️ Em ambiente distribuído real, substitua os IPs pelo endereço de cada máquina.

Cada nó deve ter:

* Um **ID único**
* Uma **porta diferente**

---

## Inicialização do Sistema (Ambiente com 3 Máquinas)

Esta seção descreve como executar o sistema em **três máquinas diferentes**, conectadas na mesma rede local.

### Exemplo de cenário

* **Máquina 1** → Nó 1 (Middleware + MySQL)
* **Máquina 2** → Nó 2 (Middleware + MySQL)
* **Máquina 3** → Nó 3 (Middleware + MySQL – Coordenador inicial)

Cada máquina executa **uma instância do middleware** e **uma instância do MySQL**.

---

### 1️. Iniciar os nós do middleware (uma máquina por nó)

Em cada máquina, execute:

```bash
python middleware.py config.json
```

Saída esperada:

```
[*] Nó X iniciado em <IP>:<PORTA>
[*] Coordenador atual: Nó Y
[*] Heartbeat check...
```

---

Em terminais separados (ou máquinas diferentes):

```bash
python middleware.py config1.json
python middleware.py config2.json
python middleware.py config3.json
```

Cada nó exibirá:

* Seu ID e endereço
* O coordenador atual
* Mensagens de heartbeat

---

## Uso do Cliente (Pode rodar em qualquer máquina)

O cliente pode ser executado em **qualquer uma das máquinas** ou até em uma **quarta máquina**, desde que tenha acesso à rede.

---

### 2️. Iniciar o cliente

```bash
python client.py
```

O cliente solicitará:

```
IP do nó middleware:
Porta do nó:
```

Informe o IP e a porta de **qualquer nó ativo**.

### Comandos disponíveis

* `:node` → trocar o nó conectado
* `:info` → exibir informações do nó atual
* `:exit` → encerrar o cliente
* Qualquer outro comando é tratado como **SQL**

---

## Exemplo de Execução

### Escrita

```sql
INSERT INTO teste VALUES (1);
```

Saída:

```
[!] Redirecionando para coordenador (Nó 3)
Nó executor: 3
SUCCESS: Transação replicada em todos os nós.
```

### Leitura

```sql
SELECT * FROM teste;
```

Saída:

```
Nó executor: 3
{'id': 1}
```

---

## Observações Importantes

* O sistema foi testado localmente, mas está preparado para execução em **múltiplas máquinas**.
* A implementação do 2PC é **simplificada**, com foco didático.
* O heartbeat e a eleição estão implementados de forma básica para fins acadêmicos.

---

## Limitações Conhecidas sobre o trabalho

Este projeto tem caráter **didático e acadêmico**, portanto algumas simplificações foram adotadas para reduzir a complexidade da implementação.

### Descoberta do Coordenador no Cliente

Atualmente, o cliente realiza o redirecionamento automático para o nó coordenador utilizando um **mapeamento fixo de IDs para IP/porta**. Isso implica que:

- O cliente possui conhecimento prévio da topologia do cluster
- Mudanças de IP, porta ou quantidade de nós exigem atualização manual no cliente

Essa abordagem **não é ideal para sistemas distribuídos em produção**, mas foi adotada para:

- Simplificar o código do cliente
- Facilitar testes em ambiente acadêmico
- Tornar o comportamento do sistema mais previsível durante a demonstração

Em um sistema real, essa limitação poderia ser resolvida por meio de:

- Retorno dinâmico do endereço do coordenador pelo middleware
- Serviço de descoberta (ex.: ZooKeeper, etcd, Consul)
- Configuração externa ou DNS distribuído

---

## Conclusão

Este projeto demonstra conceitos fundamentais de **sistemas distribuídos**, incluindo coordenação, replicação, consistência e comunicação entre nós, servindo como base para evoluções futuras como tolerância avançada a falhas, balanceamento de carga e replicação assíncrona.