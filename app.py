from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
import time
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db:5432/guild'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    credit_bucket = db.Column(db.Integer, default=0)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    members = db.relationship('Member', secondary='task_assignments', backref='tasks')

class TaskAssignments(db.Model):
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('member.id'), primary_key=True)

@app.route('/members', methods=['POST'])
def register_member():
    data = request.get_json()
    new_member = Member(name=data['name'])
    db.session.add(new_member)
    db.session.commit()
    return jsonify({'id': new_member.id, 'name': new_member.name, 'credit_bucket': new_member.credit_bucket}), 201

@app.route('/members', methods=['GET'])
def list_members():
    members = Member.query.all()
    return jsonify([{'id': member.id, 'name': member.name, 'credit_bucket': member.credit_bucket} for member in members])

@app.route('/members/<int:member_id>', methods=['GET'])
def get_member(member_id):
    member = Member.query.get_or_404(member_id)
    return jsonify({'id': member.id, 'name': member.name, 'credit_bucket': member.credit_bucket})

@app.route('/members/<int:member_id>', methods=['PUT'])
def update_member(member_id):
    data = request.get_json()
    member = Member.query.get_or_404(member_id)
    member.name = data['name']
    db.session.commit()
    return jsonify({'id': member.id, 'name': member.name, 'credit_bucket': member.credit_bucket})

@app.route('/members/<int:member_id>', methods=['DELETE'])
def delete_member(member_id):
    member = Member.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    return '', 204

@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    new_task = Task(description=data['description'], credits=data['credits'])
    db.session.add(new_task)
    db.session.commit()
    return jsonify({'id': new_task.id, 'description': new_task.description, 'credits': new_task.credits, 'status': new_task.status}), 201

@app.route('/tasks', methods=['GET'])
def list_tasks():
    tasks = Task.query.all()
    return jsonify([{'id': task.id, 'description': task.description, 'credits': task.credits, 'status': task.status} for task in tasks])

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify({'id': task.id, 'description': task.description, 'credits': task.credits, 'status': task.status})

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.get_json()
    task = Task.query.get_or_404(task_id)
    task.description = data['description']
    task.credits = data['credits']
    db.session.commit()
    return jsonify({'id': task.id, 'description': task.description, 'credits': task.credits, 'status': task.status})

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return '', 204

@app.route('/tasks/<int:task_id>/assign', methods=['POST'])
def assign_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    for member_id in data['member_ids']:
        member = Member.query.get(member_id)
        if member:
            task.members.append(member)
    db.session.commit()
    return jsonify({'id': task.id, 'members': [member.id for member in task.members]})

@app.route('/tasks/<int:task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    task.status = data['status']
    if task.status == 'completed':
        credits_per_member = task.credits // len(task.members)
        for member in task.members:
            member.credit_bucket += credits_per_member
    db.session.commit()
    return jsonify({'id': task.id, 'status': task.status})

@app.route('/tasks/<int:task_id>/assignment', methods=['GET'])
def get_task_assignment(task_id):
    task = Task.query.get_or_404(task_id)
    members = [{'id': member.id, 'name': member.name} for member in task.members]
    return jsonify({'id': task.id, 'description': task.description, 'members': members})

def wait_for_db():
    retries = 5
    while retries > 0:
        try:
            db.session.execute('SELECT 1')
            return True
        except Exception as e:
            print(f"Database not ready yet, retrying... {retries} retries left")
            retries -= 1
            time.sleep(2)
    return False

if __name__ == '__main__':
    if wait_for_db():
        with app.app_context():
            from flask_migrate import upgrade, init, migrate
            try:
                if not os.path.exists('migrations'):
                    init()
            except Exception as e:
                pass
            #migrate()
            upgrade()
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("Failed to connect to the database after several retries.")

