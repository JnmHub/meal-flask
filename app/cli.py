from uuid import uuid4

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models.admin import Admin
from app.utils.security import hash_password

@click.command('init-db')
@with_appcontext
def init_db():
    db.create_all()
    click.echo('数据库表已创建')

@click.command('create-super')
@click.option('--account', prompt=True)
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_super(account, password):
    admin_id = f"SUPER-{uuid4().hex[:8].upper()}"
    if Admin.query.get(admin_id):
        click.echo('超级管理员已存在(id=SUPER)')
        return
    a = Admin(id=admin_id, account=account, password_hash=hash_password(password), display_name='超级管理员')
    db.session.add(a)
    db.session.commit()
    click.echo(f'已创建超级管理员: {account} (id={admin_id})')

def register_cli(app):
    app.cli.add_command(init_db)
    app.cli.add_command(create_super)
