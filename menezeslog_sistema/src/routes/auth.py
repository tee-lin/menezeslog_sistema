from flask import Blueprint, request, jsonify, current_app
import jwt
import datetime
from functools import wraps
from src.models.models import db, User

auth_bp = Blueprint('auth', __name__)

# Decorator para verificar token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Verificar se o token está no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        # Verificar se o token está nos cookies
        if not token and 'token' in request.cookies:
            token = request.cookies['token']
        
        # Verificar se o token está nos parâmetros da URL
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'message': 'Token não fornecido!'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['id']).first()
            
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
    
    if not data:
        # Tentar obter dados do formulário
        username = request.form.get('username')
        password = request.form.get('password')
    else:
        username = data.get('username')
        password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user:
        return jsonify({'message': 'Usuário não encontrado!'}), 401
    
    if not user.check_password(password):
        return jsonify({'message': 'Senha incorreta!'}), 401
    
    if not user.active:
        return jsonify({'message': 'Usuário inativo!'}), 401
    
    # Gerar token JWT
    token = jwt.encode({
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    # Verificar se é primeiro acesso
    first_access = user.first_access
    if first_access:
        user.first_access = False
        db.session.commit()
    
    return jsonify({
        'message': 'Login realizado com sucesso!',
        'token': token,
        'user': {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'driver_id': user.driver_id,
            'first_access': first_access
        }
    }), 200

# Rota para verificar token
@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    return jsonify({
        'message': 'Token válido!',
        'user': {
            'id': current_user.id,
            'username': current_user.username,
            'name': current_user.name,
            'email': current_user.email,
            'role': current_user.role,
            'driver_id': current_user.driver_id
        }
    }), 200

# Rota para alterar senha
@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    if not current_user.check_password(data.get('current_password')):
        return jsonify({'message': 'Senha atual incorreta!'}), 401
    
    current_user.set_password(data.get('new_password'))
    db.session.commit()
    
    return jsonify({'message': 'Senha alterada com sucesso!'}), 200

# Rota para redefinir senha (primeiro acesso ou esqueceu a senha)
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    
    if not data or not data.get('username'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user:
        return jsonify({'message': 'Usuário não encontrado!'}), 404
    
    # Gerar nova senha aleatória
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    new_password = ''.join(secrets.choice(alphabet) for i in range(8))
    
    user.set_password(new_password)
    user.first_access = True
    db.session.commit()
    
    # Aqui seria enviado um e-mail com a nova senha
    # Por enquanto, apenas retornamos a senha para fins de demonstração
    return jsonify({
        'message': 'Senha redefinida com sucesso!',
        'new_password': new_password
    }), 200

# Rota para listar usuários (apenas admin)
@auth_bp.route('/users', methods=['GET'])
@token_required
def list_users(current_user):
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    users = User.query.all()
    
    return jsonify({
        'users': [user.to_dict() for user in users]
    }), 200

# Rota para criar usuário (apenas admin)
@auth_bp.route('/users', methods=['POST'])
@token_required
def create_user(current_user):
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('email') or not data.get('role'):
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Verificar se usuário já existe
    if User.query.filter_by(username=data.get('username')).first():
        return jsonify({'message': 'Usuário já existe!'}), 400
    
    # Verificar se e-mail já existe
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'message': 'E-mail já cadastrado!'}), 400
    
    # Gerar senha aleatória
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(8))
    
    # Criar usuário
    user = User(
        username=data.get('username'),
        email=data.get('email'),
        role=data.get('role'),
        name=data.get('name', ''),
        driver_id=data.get('driver_id'),
        active=True,
        first_access=True
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Usuário criado com sucesso!',
        'user': user.to_dict(),
        'password': password
    }), 201

# Rota para obter detalhes de um usuário (apenas admin)
@auth_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    user = User.query.get_or_404(user_id)
    
    return jsonify({
        'user': user.to_dict()
    }), 200

# Rota para atualizar usuário (apenas admin ou o próprio usuário)
@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    if current_user.role != 'admin' and current_user.id != user_id:
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    user = User.query.get_or_404(user_id)
    
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'Dados incompletos!'}), 400
    
    # Atualizar campos
    if 'name' in data:
        user.name = data.get('name')
    
    if 'email' in data and current_user.role == 'admin':
        # Verificar se e-mail já existe
        if User.query.filter(User.email == data.get('email'), User.id != user_id).first():
            return jsonify({'message': 'E-mail já cadastrado!'}), 400
        
        user.email = data.get('email')
    
    if 'role' in data and current_user.role == 'admin':
        user.role = data.get('role')
    
    if 'driver_id' in data and current_user.role == 'admin':
        user.driver_id = data.get('driver_id')
    
    if 'active' in data and current_user.role == 'admin':
        user.active = data.get('active')
    
    db.session.commit()
    
    return jsonify({
        'message': 'Usuário atualizado com sucesso!',
        'user': user.to_dict()
    }), 200

# Rota para excluir usuário (apenas admin)
@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user.role != 'admin':
        return jsonify({'message': 'Acesso não autorizado!'}), 403
    
    if current_user.id == user_id:
        return jsonify({'message': 'Não é possível excluir o próprio usuário!'}), 400
    
    user = User.query.get_or_404(user_id)
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({
        'message': 'Usuário excluído com sucesso!'
    }), 200
