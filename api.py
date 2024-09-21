from flask_restful import Resource, Api, reqparse
from app import app
from flask import jsonify
from models import db, Campaign, AdRequest, User, InfluencerCampaignRequest

api = Api(app)

user_parser = reqparse.RequestParser()
user_parser.add_argument('username', type=str, required=True, help='Username cannot be blank')
user_parser.add_argument('password', type=str, required=True, help='Password cannot be blank')
user_parser.add_argument('role', type=str, required=True, help='Role cannot be blank')
user_parser.add_argument('name', type=str)
user_parser.add_argument('company', type=str)
user_parser.add_argument('industry', type=str)
user_parser.add_argument('budget', type=float)
user_parser.add_argument('niche', type=str)
user_parser.add_argument('platform_preferences', type=str)
user_parser.add_argument('reach', type=int)

campaign_parser = reqparse.RequestParser()
campaign_parser.add_argument('name', type=str, required=True, help='Name cannot be blank')
campaign_parser.add_argument('description', type=str)
campaign_parser.add_argument('category', type=str, required=True, help='Category cannot be blank')
campaign_parser.add_argument('budget', type=float, required=True, help='Budget cannot be blank')
campaign_parser.add_argument('status', type=str, default='active')
campaign_parser.add_argument('visibility', type=str, default='public')
campaign_parser.add_argument('start_date', type=str, required=True, help='Start date cannot be blank')
campaign_parser.add_argument('end_date', type=str, required=True, help='End date cannot be blank')
campaign_parser.add_argument('goal', type=str)
campaign_parser.add_argument('sponsor_id', type=int, required=True, help='Sponsor ID cannot be blank')
campaign_parser.add_argument('influencer_id', type=int)

class UserResource(Resource):
    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        return jsonify({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'name': user.name,
            'company': user.company,
            'industry': user.industry,
            'budget': user.budget,
            'niche': user.niche,
            'platform_preferences': user.platform_preferences,
            'reach': user.reach
        })

    def delete(self, user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return '', 204

    def put(self, user_id):
        args = user_parser.parse_args()
        user = User.query.get_or_404(user_id)
        user.username = args['username']
        user.password = args['password']
        user.role = args['role']
        user.name = args.get('name')
        user.company = args.get('company')
        user.industry = args.get('industry')
        user.budget = args.get('budget')
        user.niche = args.get('niche')
        user.platform_preferences = args.get('platform_preferences')
        user.reach = args.get('reach')
        db.session.commit()
        return {"message": "Updated Successfully"}, 200


class UserListResource(Resource):
    def get(self):
        users = User.query.all()
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'name': user.name,
            'company': user.company,
            'industry': user.industry,
            'budget': user.budget,
            'niche': user.niche,
            'platform_preferences': user.platform_preferences,
            'reach': user.reach
        } for user in users])

    def post(self):
        args = user_parser.parse_args()
        user = User(
            username=args['username'],
            password=args['password'],
            role=args['role'],
            name=args.get('name'),
            company=args.get('company'),
            industry=args.get('industry'),
            budget=args.get('budget'),
            niche=args.get('niche'),
            platform_preferences=args.get('platform_preferences'),
            reach=args.get('reach')
        )
        try:
            db.session.add(user)
            db.session.commit()
            return {"message": "Posted Successfully"}, 201
        except Exception as e:
            db.session.rollback()
            return {"message": "An Error in posting"}, 400


class CampaignApi(Resource):
    def get(self, campaign_id):
        campaign = Campaign.query.get_or_404(campaign_id)
        return jsonify({
            'id': campaign.id,
            'name': campaign.name,
            'description': campaign.description,
            'category': campaign.category,
            'budget': campaign.budget,
            'status': campaign.status,
            'visibility': campaign.visibility,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'goal': campaign.goal,
            'sponsor_id': campaign.sponsor_id,
            'influencer_id': campaign.influencer_id
        })

    def delete(self, campaign_id):
        campaign = Campaign.query.get_or_404(campaign_id)
        db.session.delete(campaign)
        db.session.commit()
        return '', 204

    def put(self, campaign_id):
        args = campaign_parser.parse_args()
        campaign = Campaign.query.get_or_404(campaign_id)
        for key, value in args.items():
            if value is not None:
                setattr(campaign, key, value)
        db.session.commit()
        return jsonify({
            'id': campaign.id,
            'name': campaign.name,
            'description': campaign.description,
            'category': campaign.category,
            'budget': campaign.budget,
            'status': campaign.status,
            'visibility': campaign.visibility,
            'start_date': campaign.start_date,
            'end_date': campaign.end_date,
            'goal': campaign.goal,
            'sponsor_id': campaign.sponsor_id,
            'influencer_id': campaign.influencer_id
        })

class CampaignListApi(Resource):
    def get(self, campaign_id):
        campaigns = Campaign.query.filter_by(id=campaign_id).all()
        user_campaigns = []
        for campaign in campaigns:
            campaign_details = {
                'id': campaign.id,
                'name': campaign.name,
                'description': campaign.description,
                'category': campaign.category,
                'budget': campaign.budget,
                'status': campaign.status,
                'visibility': campaign.visibility,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'goal': campaign.goal,
                'sponsor_id': campaign.sponsor_id,
                'influencer_id': campaign.influencer_id,
            }
            user_campaigns.append(campaign_details)
        return user_campaigns

    def post(self,campaign_id):
        args = campaign_parser.parse_args()
        campaign = Campaign(**args)
        db.session.add(campaign)
        db.session.commit()
        return {"message":"campaign created"}, 201
    def put(self,campaign_id):
        args = campaign_parser.parse_args()
        campaign = Campaign.query.filter_by(id=campaign_id).first()
        if campaign:
            for key, value in args.items():
                setattr(campaign, key, value)
                db.session.commit()
                return {"message":"campaign updated"}, 200
        else:
            return {"message":"campaign not found"}, 404
    def delete(self,campaign_id):
        campaign = Campaign.query.filter_by(id=campaign_id).first()
        if campaign:
            db.session.delete(campaign)
            return {"message":"campaign deleted"},200
        else:
            return {"message":"campaign not found"}, 404
            

api.add_resource(UserResource, '/api/users/<int:user_id>')
api.add_resource(UserListResource, '/api/users')
api.add_resource(CampaignApi, '/api/campaigns/<int:campaign_id>')
api.add_resource(CampaignListApi, '/api/campaigns/<int:campaign_id>')


