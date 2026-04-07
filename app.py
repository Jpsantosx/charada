from flask import Flask, jsonify, request
import random
import firebase_admin
from firebase_admin import credentials, firestore
from auth import token_obrigatorio, gerar_token
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from flasgger import Swagger

# Carregar variáveis de ambiente
load_dotenv()

app = Flask(__name__)
app.config['SWAGGER'] = {
    'openapi': '3.0.0'
}

swagger = Swagger(app, template_file='openapi.yaml')

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# Configuração do CORS para permitir o acesso do seu frontend na Vercel
CORS(app, origins=["https://projeto-charada.vercel.app"])

ADM_USUARIO = os.getenv("ADM_USUARIO")
ADM_SENHA = os.getenv("ADM_SENHA")

# Inicialização do Firebase
if os.getenv("VERCEL"):
     cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS")))
else:
     cred = credentials.Certificate("firebase.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

# --- ROTAS PÚBLICAS ---

@app.route("/", methods=['GET'])
def root():
    return jsonify({
        "api": "charadas",
        "version": "1.0",
        "Author": "João Pedro Stadler"
    }), 200

@app.route("/login", methods=["POST"])
def login():
     dados = request.get_json()

     if not dados:
          return jsonify({"error": "Envie os dados para o login"}), 400
     
     usuario = dados.get("usuario")
     senha = dados.get("senha")

     if not usuario or not senha:
          return jsonify({"error": "Usuário e Senha são obrigatórios"}), 400
     
     if usuario == ADM_USUARIO and senha == ADM_SENHA:
          token = gerar_token(usuario)
          return jsonify({"message": "Login realizado com sucesso", "token": token}), 200
     
     return jsonify({"error": "Usuário ou senha inválidos"}), 401

@app.route("/charadas", methods=['GET'])     
def get_charadas():
     charadas = []
     lista = db.collection('charadas').stream()

     for item in lista:
          charadas.append(item.to_dict())
     return jsonify(charadas), 200

@app.route("/charadas/aleatorias", methods=['GET'])
def get_charadas_random():
     charadas = []
     lista = db.collection('charadas').stream()

     for item in lista:
          charadas.append(item.to_dict())
     
     if not charadas:
          return jsonify({"error": "Nenhuma charada encontrada no banco"}), 404
          
     return jsonify(random.choice(charadas)), 200

@app.route("/charadas/<int:id>", methods=['GET'])
def get_charada_by_id(id):
     lista = db.collection('charadas').where('id', '==', id).stream()
     for item in lista:
          return jsonify(item.to_dict()), 200
     
     return jsonify({"error": "Charada não encontrada"}), 404

# --- ROTAS PRIVADAS ---

@app.route("/charadas", methods=['POST'])
@token_obrigatorio
def post_charadas():
     dados = request.get_json()

     if not dados or "pergunta" not in dados or "resposta" not in dados:
          return jsonify({"error": "Dados inválidos ou incompletos!"}), 400
     
     try:
          contador_ref = db.collection("contador").document("controle_id")
          contador_doc = contador_ref.get()
          ultimo_id = contador_doc.to_dict().get("ultimo_id")
          
          novo_id = ultimo_id + 1
          contador_ref.update({"ultimo_id": novo_id})

          db.collection("charadas").add({
               "id": novo_id,
               "pergunta": dados["pergunta"],
               "resposta": dados["resposta"]
          })

          return jsonify({"message": "Charada criada com sucesso!"}), 201
     except Exception as e:   
          return jsonify({"error": f"Falha ao processar requisição: {str(e)}"}), 500

@app.route("/charadas/<int:id>", methods=['PUT'])
@token_obrigatorio
def charadas_put(id):
     dados = request.get_json()

     if not dados or "pergunta" not in dados or "resposta" not in dados:
          return jsonify({"error": "Dados inválidos ou incompletos!"}), 400
     
     try: 
          docs = db.collection("charadas").where("id", "==", id).limit(1).get()
          if not docs:
               return jsonify({"error": "Charada não encontrada"}), 404
          
          for doc in docs:
               doc_ref = db.collection("charadas").document(doc.id)
               doc_ref.update({
                    "pergunta": dados["pergunta"],
                    "resposta": dados["resposta"]
               })

          return jsonify({"message": "Charada alterada com sucesso"}), 200
     except:
          return jsonify({"error": "Falha na atualização da charada"}), 400

@app.route("/charadas/<int:id>", methods=['PATCH'])
@token_obrigatorio
def charadas_patch(id):
     dados = request.get_json()

     if not dados or ("pergunta" not in dados and "resposta" not in dados):
          return jsonify({"error": "Envie ao menos um campo para alteração"}), 400
     
     try: 
          docs = db.collection("charadas").where("id", "==", id).limit(1).get()
          if not docs:
               return jsonify({"error": "Charada não encontrada"}), 404
          
          doc_ref = db.collection("charadas").document(docs[0].id)
          update_charada = {}
          
          if "pergunta" in dados:
               update_charada["pergunta"] = dados["pergunta"]
          if "resposta" in dados:
               update_charada["resposta"] = dados["resposta"]

          doc_ref.update(update_charada)
          return jsonify({"message": "Charada alterada com sucesso"}), 200
     
     except:
          return jsonify({"error": "Falha na atualização parcial da charada"}), 400

@app.route("/charadas/<int:id>", methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):
     docs = db.collection("charadas").where("id", "==", id).limit(1).get()

     if not docs:
          return jsonify({"error": "Charada não encontrada"}), 404
     
     doc_ref = db.collection("charadas").document(docs[0].id)
     doc_ref.delete()
     return jsonify({"message": "Charada excluída com sucesso!"}), 200

# --- TRATAMENTO DE ERROS ---

@app.errorhandler(404)
def erro404(error):
     return jsonify({"error": "Recurso não encontrado"}), 404

@app.errorhandler(500)
def erro500(error):
     return jsonify({"error": "Servidor interno com falhas. Tente mais tarde"}), 500

if __name__ == "__main__":
    app.run(debug=True)