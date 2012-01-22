import os.path
from datetime import datetime
from flask import json
from flaskext.sqlalchemy import SQLAlchemy
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    openid_url = db.Column(db.Text())
    name = db.Column(db.Text())
    email = db.Column(db.Text())


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    person = db.relationship('Person',
        backref=db.backref('properties', lazy='dynamic'))
    name = db.Column(db.String(30))
    value = db.Column(db.Text())


class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', primaryjoin=(user_id==User.id),
        backref=db.backref('suggestions', lazy='dynamic'))
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    person = db.relationship('Person',
        backref=db.backref('suggestions', lazy='dynamic'))
    name = db.Column(db.String(30))
    value = db.Column(db.Text())
    date = db.Column(db.DateTime(timezone=True))
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    admin = db.relationship('User', primaryjoin=(admin_id==User.id),
        backref=db.backref('decisions', lazy='dynamic'))
    decision = db.Column(db.String(10))


def get_persons():
    results = {}

    for person in Person.query.all():
        results[person.id] = person_data = {'name': person.name}

        for prop in person.properties.all():
            person_data[prop.name] = prop.value

    return results


def save_suggestion(user, person_id, name, value):
    person = Person.query.get_or_404(person_id)
    suggestion = Suggestion(user=user,
                            person=person,
                            name=name,
                            value=value,
                            date=datetime.utcnow())
    db.session.add(suggestion)
    db.session.commit()

    log.info('New suggestion %d from %r: name=%r, value=%r',
             suggestion.id, user, name, value)

    return suggestion


def decision(suggestion_id, admin, decision):
    suggestion = Suggestion.query.get(suggestion_id)

    if decision == 'accept':
        person = suggestion.person
        value = suggestion.value
        prop = person.properties.filter_by(name=suggestion.name).first()
        if prop is None:
            prop = Property(person=person, name=suggestion.name)
        prop.value = suggestion.value
        db.session.add(prop)

    suggestion.admin = admin
    suggestion.decision = decision

    db.session.add(suggestion)
    db.session.commit()

    log.info('Suggestion %d decision: %s by %r',
             suggestion_id, decision, admin.openid_url)

    return suggestion


def import_fixture(flush=True):
    data_path = os.path.join(os.path.dirname(__file__), 'data')
    fixture_path = os.path.join(data_path, 'fixture.json')

    if flush:
        db.drop_all()
        db.create_all()

    with open(fixture_path, 'rb') as f:
        fixture = json.load(f)

    for person_data in fixture:

        person = Person(id=person_data.pop('id'), name=person_data.pop('name'))
        db.session.add(person)

        for key in person_data:
            prop = Property(person=person, name=key, value=person_data[key])
            db.session.add(prop)

    db.session.commit()


def get_user(openid_url):
    return User.query.filter_by(openid_url=openid_url).first()


def get_update_user(openid_url, name, email):
    user = get_user(openid_url)
    if user is None:
        user = User(openid_url=openid_url)

    if (name, email) != (user.name, user.email):
        user.name = name
        user.email = email
        db.session.add(user)
        db.session.commit()

    return user
