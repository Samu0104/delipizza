from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# Criação da aplicação Flask
app = Flask(__name__)
app.secret_key = '123'  # Chave secreta para sessões

# Função para obter a conexão com o banco de dados SQLite
def get_db_connection():
    try:
        conn = sqlite3.connect('BancoDeDados.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

# Criando função para criação do banco de dados 
def create_table():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()

        # Criação da tabela de pizzas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_pizza( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_pizza TEXT NOT NULL,
            descricao TEXT NOT NULL, 
            preco_p REAL NOT NULL,
            preco_m REAL NOT NULL,
            preco_g REAL NOT NULL,
            preco_gg REAL NOT NULL
            )
        ''')

        # Criação da tabela de sobremesas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_sobremesa( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_sobremesa TEXT NOT NULL,
            preco REAL NOT NULL
            )
        ''')

        # Criação da tabela de bebidas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cardapio_bebidas( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_bebida TEXT NOT NULL,
            preco REAL NOT NULL 
            )
        ''')

        # Criação da tabela de contas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conta( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            idade INTEGER NOT NULL,
            telefone TEXT NOT NULL,
            senha TEXT NOT NULL
            )
        ''')

        # Criação da tabela de itens curtidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS itens_curtidos( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,  -- 'pizza', 'sobremesa' ou 'bebida'
            item_id INTEGER NOT NULL
            )
        ''')

        # Criação da tabela de carrinho
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carrinho( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL,  -- 'pizza', 'sobremesa' ou 'bebida'
            item_id INTEGER NOT NULL
            )
        ''')

        # Criação da tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos( 
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES conta (id)
            )
        ''')

        conn.commit()  # Salva as alterações
        conn.close()   # Fecha a conexão

@app.route('/')
def home():
    return render_template('index.html')

# Rota para registro de conta
@app.route('/cadastrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        idade = request.form['idade']
        telefone = request.form['telefone']
        senha = request.form['senha']
        
        hashed_senha = generate_password_hash(senha)  # Hash da senha
        
        conn = get_db_connection()
        if conn:
            try:
                conn.execute('INSERT INTO conta (nome, email, idade, telefone, senha) VALUES (?, ?, ?, ?, ?)',
                             (nome, email, idade, telefone, hashed_senha))
                conn.commit()
                return redirect('/login')  # Redireciona para a página de login após o registro
            except sqlite3.IntegrityError:
                return "Email já cadastrado. Tente outro."
            finally:
                conn.close()

    return render_template('cadastrar.html')

# Rota para login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form ['senha']
        
        conn = get_db_connection()
        if conn:
            user = conn.execute('SELECT * FROM conta WHERE email = ?', (email,)).fetchone()
            if user and check_password_hash(user['senha'], senha):
                session['user_id'] = user['id']  
                return redirect('/')  # Redireciona para a página inicial após o login
            else:
                return "Email ou senha incorretos."
            conn.close()

    return render_template('login.html')

# Rota para adicionar itens ao carrinho
@app.route('/adicionar_ao_carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    data = request.get_json()
    tipo = data.get('tipo')
    item_id = data.get('item_id')

    if tipo and item_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO carrinho (tipo, item_id) VALUES (?, ?)', (tipo, item_id))
            conn.commit()
            return jsonify({'status': 'success', 'message': f'{item_id} adicionado ao carrinho!'})
        except sqlite3.Error as e:
            return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500
        finally:
            conn.close()
    else:
        return jsonify({'status': 'error', 'message': 'Dados inválidos!'}), 400

# Rota para finalizar a compra
@app.route('/compra', methods=['POST'])
def compra():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Obter todos os itens do carrinho
        itens_carrinho = cursor.execute('SELECT * FROM carrinho').fetchall()

        if not itens_carrinho:
            return jsonify({'status': 'error', 'message': 'Carrinho vazio!'}), 400

        # Calcular o total da compra
        total = 0
        for item in itens_carrinho:
            if item['tipo'] == 'pizza':
                pizza = cursor.execute('SELECT preco_p FROM cardapio_pizza WHERE id = ?', (item['item_id'],)).fetchone()
                if pizza:
                    total += pizza['preco_p']
            elif item['tipo'] == 'sobremesa':
                sobremesa = cursor.execute('SELECT preco FROM cardapio_sobremesa WHERE id = ?', (item['item_id'],)).fetchone()
                if sobremesa:
                    total += sobremesa['preco']
            elif item['tipo'] == 'bebida':
                bebida = cursor.execute('SELECT preco FROM cardapio_bebidas WHERE id = ?', (item['item_id'],)).fetchone()
                if bebida:
                    total += bebida['preco']

        # Obter o ID do usuário da sessão
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'status': 'error', 'message': 'Usuário não autenticado!'}), 401

        # Inserir o pedido na tabela de pedidos
        cursor.execute('INSERT INTO pedidos (user_id, total, data) VALUES (?, ?, datetime("now"))', (user_id, total))
        conn.commit()

        # Limpar o carrinho após a compra
        cursor.execute('DELETE FROM carrinho')
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Compra finalizada com sucesso!', 'total': total})
    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}),  500
    finally:
        conn.close()

# Rota para exibir o carrinho
@app.route('/carrinho', methods=['GET'])
def carrinho():
    conn = get_db_connection()
    cursor = conn.cursor()
    itens_carrinho = cursor.execute('SELECT * FROM carrinho').fetchall()

    # Obter detalhes dos itens
    detalhes_itens = []
    for item in itens_carrinho:
        if item['tipo'] == 'pizza':
            pizza = cursor.execute('SELECT nome_pizza, preco_p FROM cardapio_pizza WHERE id = ?', (item['item_id'],)).fetchone()
            if pizza:
                detalhes_itens.append({'nome': pizza['nome_pizza'], 'tipo': 'pizza', 'preco': pizza['preco_p']})
        elif item['tipo'] == 'sobremesa':
            sobremesa = cursor.execute('SELECT nome_sobremesa, preco FROM cardapio_sobremesa WHERE id = ?', (item['item_id'],)).fetchone()
            if sobremesa:
                detalhes_itens.append({'nome': sobremesa['nome_sobremesa'], 'tipo': 'sobremesa', 'preco': sobremesa['preco']})
        elif item['tipo'] == 'bebida':
            bebida = cursor.execute('SELECT nome_bebida, preco FROM cardapio_bebidas WHERE id = ?', (item['item_id'],)).fetchone()
            if bebida:
                detalhes_itens.append({'nome': bebida['nome_bebida'], 'tipo': 'bebida', 'preco': bebida['preco']})

    conn.close()
    return render_template('carrinho.html', itens=detalhes_itens)

if __name__ == '__main__':
    create_table()  # Cria as tabelas no banco de dados
    app.run(debug=True)