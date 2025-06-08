from src.main import app, db

with app.app_context():
    db.create_all()
    print("Tabelas criadas com sucesso!")
