import os
import click
from app import create_app, db
from app.models.user import User

app = create_app(os.getenv('FLASK_CONFIG', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Add database and models to Flask shell context."""
    from app.models.child import Child
    return {'db': db, 'User': User, 'Child': Child}


@app.cli.command('create-admin')
@click.option('--name', prompt='Admin Name', help='Administrator full name')
@click.option('--email', prompt='Admin Email', help='Administrator email address')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Administrator password')
def create_admin(name, email, password):
    """CLI utility to provision a platform administrator."""
    normalized_email = email.strip().lower()
    existing_user = User.query.filter_by(email=normalized_email).first()
    if existing_user:
        click.echo(f"Error: A user with email '{normalized_email}' already exists.")
        return

    admin = User(
        name=name.strip(),
        email=normalized_email,
        role='admin',
        is_active=True
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f"Administrator account '{normalized_email}' created successfully.")


@app.cli.command('seed-activities')
def seed_activities_cmd():
    """CLI utility to seed demo categories, activities, and questions."""
    from app.utils.seed_data import seed_activities
    cats, acts, quests = seed_activities()
    click.echo(f"Seeded {cats} categories, {acts} activities, and {quests} questions successfully.")


def run_seed_demo(fresh: bool = False):
    """Core logic to seed/verify demo dataset with clear output logging."""
    from app.utils.seed_data import seed_demo_data
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Unknown')
    click.echo("==================================================")
    click.echo(f"Database Target: {db_uri}")
    click.echo(f"Mode: {'Fresh reseed' if fresh else 'Idempotent verify & seed'}")
    click.echo("Seeding demo dataset (activities, users, children, sessions, recommendations)...")
    res = seed_demo_data(fresh=fresh)
    click.echo("==================================================")
    click.echo("Demo Data Environment Ready!")
    click.echo(f"  Users in DB:     {res['users_after']} total (before: {res['users_before']}, new: +{res['created_users']})")
    click.echo(f"  Categories:      {res['total_categories']} available ({res['created_categories']} newly created)")
    click.echo(f"  Activities:      {res['total_activities']} interactive activities ({res['created_activities']} newly created)")
    click.echo(f"  Questions:       {res['total_questions']} questions ({res['created_questions']} newly created)")
    click.echo(f"  Demo Accounts:   {len(res['demo_users'])} verified ({', '.join(res['demo_users'])})")
    click.echo(f"  Demo Children:   {len(res['demo_children'])} profiles ({', '.join(res['demo_children'])})")
    click.echo(f"  Demo Sessions:   {res['demo_sessions']} completed sessions ({res['created_sessions']} newly created)")
    click.echo(f"  Total Sessions:  {res['total_sessions']} in database")
    click.echo("==================================================")
    click.echo("Verified Demo Credentials (Password: DemoPass123!):")
    click.echo("  Admin:   admin@childinsight.demo")
    click.echo("  Teacher: teacher@childinsight.demo")
    click.echo("  Parent:  parent@childinsight.demo")
    click.echo("==================================================")
    return res


@app.cli.command('seed-demo')
@click.option('--fresh', is_flag=True, default=False, help='Wipe existing demo sessions/children before reseeding')
def seed_demo_cmd(fresh=False):
    """CLI utility to seed a complete demo environment with users, children, sessions, and recommendations."""
    run_seed_demo(fresh=fresh)


@app.cli.command('seed-demo-data')
@click.option('--fresh', is_flag=True, default=False, help='Wipe existing demo sessions/children before reseeding')
def seed_demo_data_cmd(fresh=False):
    """Alias for seed-demo."""
    run_seed_demo(fresh=fresh)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in ('seed-demo', 'seed-demo-data'):
        fresh_flag = '--fresh' in sys.argv
        with app.app_context():
            run_seed_demo(fresh=fresh_flag)
    else:
        app.run(host='127.0.0.1', port=5000)
