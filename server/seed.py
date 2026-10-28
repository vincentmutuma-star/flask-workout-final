from server.config import create_app, db
from server.models import User, Workout
from faker import Faker
from datetime import date
import random

fake = Faker()
app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    # Create users
    u1 = User(username="vincent")
    u1.password_hash = "password123"
    u2 = User(username="testuser")
    u2.password_hash = "password123"

    db.session.add_all([u1, u2])
    db.session.commit()

    workouts = []
    for i in range(15):
        w = Workout(
            name=fake.word() + " workout",
            duration=random.randint(20, 120),
            date=date.today(),
            user_id=u1.id if i < 10 else u2.id
        )
        workouts.append(w)

    db.session.add_all(workouts)
    db.session.commit()
    print("Seeded!")