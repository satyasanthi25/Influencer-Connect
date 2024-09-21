from app import app
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy(app)

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    passhash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(50), nullable=True)

    # For Sponsors
    company = db.Column(db.String(100), nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    budget = db.Column(db.Float, nullable=True)

    # For Influencers
    niche = db.Column(db.String(100), nullable=True)
    platform_preferences = db.Column(db.String(200), nullable=True)
    reach = db.Column(db.Integer, nullable=True)

    influencer_campaigns = db.relationship('Campaign', foreign_keys='Campaign.influencer_id', backref='influencer', lazy=True)
    sponsored_campaigns = db.relationship('Campaign', foreign_keys='Campaign.sponsor_id', backref='sponsor', lazy=True, cascade="all, delete-orphan")
    influencer_adrequests = db.relationship('AdRequest', foreign_keys='AdRequest.influencer_id', backref='influencer', lazy=True)
    sponsored_adrequests = db.relationship('AdRequest', foreign_keys='AdRequest.sponsor_id', backref='sponsor', lazy=True, cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.passhash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.passhash, password)
    

class Campaign(db.Model):
    __tablename__ = 'campaign'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="active")  # 'active', 'paused', 'completed'
    visibility = db.Column(db.String(50), nullable=False, default="public")  # 'public', 'private'
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    goal = db.Column(db.String(200), nullable=True)

    influencer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    ad_requests = db.relationship('AdRequest', backref='campaign', lazy=True, cascade="all, delete-orphan")
    influencer_campaign_requests = db.relationship('InfluencerCampaignRequest', backref='campaign', lazy=True)


class AdRequest(db.Model):
    __tablename__ = 'ad_request'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad_name = db.Column(db.String(150), nullable=False)
    platform_preferences = db.Column(db.Text, nullable=True)
    reach = db.Column(db.Integer, nullable=True)
    payment_amount = db.Column(db.Float, nullable=False)
    ad_status = db.Column(db.String(50), nullable=False, default="pending")  # 'pending', 'accepted', 'rejected'
    rating = db.Column(db.Integer, nullable=True)
    
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    influencer_campaign_requests = db.relationship('InfluencerCampaignRequest', backref='ad_request', lazy=True)


class InfluencerCampaignRequest(db.Model):
    __tablename__ = 'influencer_campaign_request'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    influencer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sponsor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ad_request_id = db.Column(db.Integer, db.ForeignKey('ad_request.id'), nullable=False)
    request_status = db.Column(db.String(50), nullable=False, default="pending")  # 'pending', 'accepted', 'rejected'
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
flagged_items = {
    'sponsor': set(),
    'influencer': set(),
    'campaign': set(),
    'ad_request': set()
}

def get_flagged_counts():
    counts = {
        'sponsors': len(flagged_items['sponsor']),
        'influencers': len(flagged_items['influencer']),
        'campaigns': len(flagged_items['campaign']),
        'ad_requests': len(flagged_items['ad_request'])
    }
    return counts    


with app.app_context():
    db.create_all()
    first_admin = User.query.filter_by(is_admin=True).first()
    if not first_admin:
        admin = User(name="Admin", username="admin", password="admin", role="admin", is_admin=True)
        db.session.add(admin)
        db.session.commit()
