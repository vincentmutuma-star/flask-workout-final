from flask import request, jsonify
from flask_restful import Api, Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt, jwt_required
from server.config import create_app, db, jwt
from server.models import User, Workout
from datetime import date

app = create_app()
api = Api(app) 

# JWT blocklist for logout (simple in-memory)
BLACKLIST = set()

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload["jti"] in BLACKLIST

# AUTH ENDPOINTS
class Register(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return {"error": "Username and password required"}, 400
        if User.query.filter_by(username=username).first():
            return {"error": "Username already exists"}, 400
        user = User(username=username)
        user.password_hash = password
        db.session.add(user)
        db.session.commit()
        access_token = create_access_token(identity=user.id)
        return {"user": user.to_dict(), "access_token": access_token}, 201

class Login(Resource):
    def post(self):
        data = request.get_json()
        user = User.query.filter_by(username=data.get('username')).first()
        if user and user.authenticate(data.get('password')):
            token = create_access_token(identity=user.id)
            return {"user": user.to_dict(), "access_token": token}, 200
        return {"error": "Invalid credentials"}, 401

class Me(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        return user.to_dict(), 200

class Logout(Resource):
    @jwt_required()
    def delete(self):
        jti = get_jwt()["jti"]
        BLACKLIST.add(jti)
        return {"message": "Logged out"}, 200

# WORKOUT CRUD + PAGINATION + PROTECTION
class Workouts(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        pagination = Workout.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page, error_out=False)
        return {
            "workouts": [w.to_dict() for w in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page
        }, 200

    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        try:
            workout = Workout(
                name=data['name'],
                duration=data['duration'],
                date=date.fromisoformat(data.get('date', str(date.today()))),
                user_id=user_id
            )
            db.session.add(workout)
            db.session.commit()
            return workout.to_dict(), 201
        except Exception as e:
            return {"error": str(e)}, 400

class WorkoutById(Resource):
    @jwt_required()
    def patch(self, id):
        user_id = get_jwt_identity()
        workout = Workout.query.get(id)
        if not workout:
            return {"error": "Workout not found"}, 404
        if workout.user_id != user_id:
            return {"error": "Unauthorized"}, 403
        data = request.get_json()
        for attr in ['name', 'duration', 'date']:
            if attr in data:
                if attr == 'date':
                    setattr(workout, attr, date.fromisoformat(data[attr]))
                else:
                    setattr(workout, attr, data[attr])
        db.session.commit()
        return workout.to_dict(), 200

    @jwt_required()
    def delete(self, id):
        user_id = get_jwt_identity()
        workout = Workout.query.get(id)
        if not workout:
            return {"error": "Workout not found"}, 404
        if workout.user_id != user_id:
            return {"error": "Unauthorized"}, 403
        db.session.delete(workout)
        db.session.commit()
        return {"message": "Deleted"}, 200

api.add_resource(Register, '/register')
api.add_resource(Login, '/login')
api.add_resource(Me, '/me')
api.add_resource(Logout, '/logout')
api.add_resource(Workouts, '/workouts')
api.add_resource(WorkoutById, '/workouts/<int:id>')

if __name__ == '__main__':
    app.run(port=5555, debug=True)