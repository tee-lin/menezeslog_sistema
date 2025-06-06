from flask import Blueprint, request, jsonify, current_app, session
from werkzeug.security import check_password_hash
from src.models.user import User
from src.models.models import db
import datetime
import jwt
from functools import wraps

auth_bp = Blueprint('auth', __name__)

# Decorator para verificar token JWT
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Verificar se o token está no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        # Verificar se o token está na sessão
        if not token and 'token' in session:
            token = session['token']
            
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401
        
        try:
            # Decodificar o token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['user_id']).first()
            
            if not current_user:
                return jsonify({'message': 'Usuário não encontrado!'}), 401
                
            if not current_user.active:
                return jsonify({'message': 'Usuário inativo!'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido!'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

# Rota de login
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Dados de login incompletos!'}), 400
        
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user:
        return jsonify({'message': 'Usuário não encontrado!'}), 401
        
    if not user.active:
        return jsonify({'message': 'Usuário inativo!'}), 401
        
    if not check_password_hash(user.password_hash, data.get('password')):
        return jsonify({'message': 'Senha incorreta!'}), 401
        
    # Atualizar último login
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()
    
    # Gerar token JWT
    token = jwt.encode({
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    # Armazenar token na sessão
    session['token'] = token
    
    return jsonify({
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'role': user.role,
            'driver_id': user.driver_id,
            'first_access': user.first_access
        }
    }), 200

# Rota para verificar se o usuário está autenticado
@auth_bp.route('/check', methods=['GET'])
@token_required
def check_auth(current_user):
    return jsonify({
        'authenticated': True,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'name': current_user.name,
            'role': current_user.role,
            'driver_id': current_user.driver_id,
            'first_access': current_user.first_access
        }
    }), 200

# Rota para logout
@auth_bp.route('/logout', methods=['POST'])
def logout():
    if 'token' in session:
        session.pop('token')
    return jsonify({'message': 'Logout realizado com sucesso!'}), 200

# Rota para alterar senha
@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Dados incompletos!'}), 400
        
    if not check_password_hash(current_user.password_hash, data.get('current_password')):
        return jsonify({'message': 'Senha atual incorreta!'}), 401
        
    current_user.set_password(data.get('new_password'))
    
    if current_user.first_access:
        current_user.first_access = False
        
    db.session.commit()
    
    return jsonify({'message': 'Senha alterada com sucesso!'}), 200

# Rota para primeiro acesso (redefinir senha)
@auth_bp.route('/first-access', methods=['POST'])
@token_required
def first_access(current_user):
    data = request.get_json()
    
    if not data or not data.get('new_password'):
        return jsonify({'message': 'Dados incompletos!'}), 400
        
    if not current_user.first_access:
        return jsonify({'message': 'Não é primeiro acesso!'}), 400
        
    current_user.set_password(data.get('new_password'))
    current_user.first_access = False
    db.session.commit()
    
    return jsonify({'message': 'Senha definida com sucesso!'}), 200
