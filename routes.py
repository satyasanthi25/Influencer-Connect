from flask import redirect, render_template, request,flash,url_for, session,jsonify
from app import app
from flask_login import login_required
from models import User,db, Campaign,AdRequest,InfluencerCampaignRequest as Request
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
from flask_login import current_user
from collections import defaultdict
from functools import wraps
from datetime import datetime



@app.route('/')
def home():
    return render_template('index.html')

#----------------login----------
@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('Please fill out all fields', 'error')
        return redirect(url_for('login'))

    user = User.query.filter_by(username=username).first()

    if not user:
        flash("Invalid username", 'error')
        return redirect(url_for('login'))
    if not user.check_password(password):
        flash("Invalid password!", 'error')
        return redirect(url_for('login'))
    if (user.id in flagged_items['sponsor'] and user.role == 'sponsor') or \
               (user.id in flagged_items['influencer'] and user.role == 'influencer'):
                flash("Your account has been flagged and you cannot log in.")
                return redirect(url_for('login'))

    
    session['user_id'] = user.id
    session['username'] = user.username
    session['user_role'] = user.role 

    if user.role == 'admin':
        flash('Login successful. Welcome, Admin!', 'success')
        return redirect(url_for('admin_home'))
    elif user.role == 'influencer':
        flash('Login successful. Welcome, Influencer!', 'success')
        return redirect(url_for('influencer_dashboard', influencer_id=user.id))
    elif user.role == 'sponsor':
        flash('Login successful. Welcome, Sponsor!', 'success')
        return redirect(url_for('sponsor_dashboard', sponsor_id=user.id))
    else:
        flash('Login successful', 'success')
        return redirect(url_for('login'))
#==========================sponsor-Dashboard===================
@app.route('/sponsor/dashboard/<int:sponsor_id>')
def sponsor_dashboard(sponsor_id):
    if 'user_id' not in session or session.get('user_role') != 'sponsor':
        return redirect(url_for('login'))

    sponsor = User.query.filter_by(id=sponsor_id, role='sponsor').first()
    if sponsor is None:
        flash('Sponsor not found.')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    campaigns = Campaign.query.filter_by(sponsor_id=sponsor_id).all()
    ad_requests = AdRequest.query.join(Campaign).filter(Campaign.sponsor_id == sponsor_id).all()

    new_requests = db.session.query(
        Request,
        User
    ).join(User, Request.influencer_id == User.id).filter(
        Request.sponsor_id == sponsor_id,
        Request.request_status == 'pending'
    ).all()
    
    campaigns_by_niche = {}
    for campaign in campaigns:
        niche = campaign.influencer.niche if campaign.influencer else "N/A"
        if niche not in campaigns_by_niche:
            campaigns_by_niche[niche] = []
        campaigns_by_niche[niche].append(campaign)

    niche = request.args.get('niche', '')
    reach = request.args.get('reach', type=int)

    return render_template(
        'sponsor_dashboard.html', 
        name=sponsor.username, 
        sponsor=sponsor, 
        campaigns_by_niche=campaigns_by_niche,
        ad_requests=ad_requests,
        sponsor_id=sponsor_id,
        new_requests=new_requests,
        niche=niche,
        reach=reach,
        active_campaigns=campaigns
    )

#--------------sponsor-Register---------
@app.route('/sponsor_register', methods=['GET','POST'])
def sponsor_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        industry = request.form.get('industry')
        role = request.form.get('role')
        budget = request.form.get('budget')
        company = request.form.get('company')

        if not username or not password or not confirm_password or not role or not budget:
            flash('Please fill out all fields')
            return redirect(url_for('sponsor_register'))
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('sponsor_register'))
        if len(username) < 5 or len(username) > 20:
            flash('Username must be between 5 and 20 characters')
            return redirect(url_for('sponsor_register'))
        
            return redirect(url_for('sponsor_register'))
        try:
            budget = float(budget)
            if budget <= 0:
                flash('Budget must be greater than 0."')
        except ValueError:
            flash("Invalid input for budget. Please enter a numeric value.")
        user = User.query.filter_by(username=username).first()

        if user:
            flash('Username already exists')
            return redirect(url_for('sponsor_register'))
        else:#model names creating the user
            password_hash = generate_password_hash(password)
            new_sponsor = User(username=username, passhash=password_hash, 
                               role=role, industry=industry,company=company, budget=budget)
            db.session.add(new_sponsor)
            db.session.commit()
            flash('You have been registered successfully,please login!')
            return redirect(url_for('login'))
    return render_template('sponsor_register.html')
#=====================influencer-Register========================
@app.route('/influencer_register', methods=['GET', 'POST'])
def influencer_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        role = request.form.get('role')
        niche = request.form.get('niche')
        reach = request.form.get('reach')
        platform_preferences = request.form.getlist('platform')

        if not username or not password or not confirm_password or not name or not niche or not reach:
            flash('Please fill out all fields')
            return redirect(url_for('influencer_register'))
        
        if password != confirm_password:
            flash('Passwords do not match')
            return redirect(url_for('influencer_register'))
        
        if int(reach) < 0:
            flash('Reach cannot be a negative value')
            return redirect(url_for('influencer_register'))
        if len(username) < 5 or len(username) > 20:
            flash('Username must be between 5 and 20 characters')
            return redirect(url_for('influencer_register'))

        if not platform_preferences:
            flash('Please select at least one platform preference')
            return redirect(url_for('influencer_register'))
        
        user = User.query.filter_by(username=username).first()

        if user:
            flash('Username already exists')
            return redirect(url_for('influencer_register'))
        else:
            password_hash = generate_password_hash(password)
            new_influencer = User(
                username=username,
                passhash=password_hash,
                role=role,
                niche=niche,
                reach=reach,
                platform_preferences=",".join(platform_preferences),
                name=name
            )
            db.session.add(new_influencer)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template('influencer_register.html')
#-------------------------------------------------------------
#auth_required decorator
def auth_required(func):
    @wraps(func)
    def inner(*args,**kwargs):
        if 'user_id' in session:
            return func(*args, **kwargs)
        else:
            flash('please login to continue')
            return redirect(url_for('login'))
    return inner

# ========profile=======================
@app.route('/profile')
@auth_required
def profile():
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/profile', methods=['POST'])
@auth_required
def profile_post():
    username = request.form.get('username')
    cpassword = request.form.get('cpassword')
    password = request.form.get('password')
    name = request.form.get('name')

    if not username or not cpassword or not password:
        flash('Please fill out all the required fields')
        return redirect(url_for('profile'))
    
    user = User.query.get(session['user_id'])
    if not check_password_hash(user.passhash, cpassword):
        flash('Incorrect password')
        return redirect(url_for('profile'))
    
    if username != user.username:
        new_username = User.query.filter_by(username=username).first()
        if new_username:
            flash('Username already exists')
            return redirect(url_for('profile'))
    
    new_password_hash = generate_password_hash(password)
    user.username = username
    user.passhash = new_password_hash
    user.name = name
    db.session.commit()
    flash('Profile updated successfully')
    return redirect(url_for('profile'))
#====================logout===============
@app.route('/logout')
@auth_required
def logout():
    session.pop('user_id')  
    return redirect(url_for('login'))


# #--------------------   CRUD-ON-CAMPAIGN---------------------------------------

@app.route('/campaign/add/<int:id>', methods=['GET', 'POST'])
def add_campaign(id):
    campaigns = Campaign.query.all()
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        try:
            budget = float(request.form.get('budget', 0))  
        except ValueError:
            flash('Budget must be a valid number')
            return redirect(url_for('add_campaign', id=id))
        status = request.form.get('status')  
        visibility = request.form.get('visibility')  
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        goal = request.form.get('goal', 0)
        influencer_id = request.form.get('influencer_id') 

        if not name or not category or not budget or not start_date_str or not end_date_str:
            flash('Please fill out all required fields')
            return redirect(url_for('add_campaign', id=id))

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.')
            return redirect(url_for('add_campaign', id=id))

        if start_date > end_date:
            flash('Start date must be before the end date')
            return redirect(url_for('add_campaign', id=id))
        if len(description) > 500:
            flash('Description is too long. Please keep it under 500 characters.')
            return redirect(url_for('add_campaign', id=id))

        try:
            goal = int(goal)
        except ValueError:
            flash('Goal must be a valid number')
            return redirect(url_for('add_campaign', id=id))

        if goal < 0:
            flash('Goal to reach subscribers cannot be negative')
            return redirect(url_for('add_campaign', id=id))

        if budget < 100 or budget > 1000000:
            flash('Budget must be between 100 and 1,000,000')
            return redirect(url_for('add_campaign', id=id))

        campaign = Campaign(
            name=name,
            description=description,
            category=category,
            budget=budget,
            status=status,
            visibility=visibility,
            start_date=start_date,
            end_date=end_date,
            goal=goal,
            influencer_id=influencer_id if influencer_id else None,
            sponsor_id=id
        )
        db.session.add(campaign)
        db.session.commit()

        flash('Campaign added successfully')
        return redirect(url_for('sponsor_dashboard', sponsor_id=id))

    return render_template('/campaign/add.html', campaigns=campaigns, id=id)

#-----------------------------------------------------------------------------
@app.route('/campaign/<int:campaign_id>', methods=['GET'])
def view_campaign(campaign_id):
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        flash('Campaign does not exist')
        return redirect(url_for('sponsor_dashboard', sponsor_id=campaign.sponsor_id))
    ad_requests = AdRequest.query.filter_by(campaign_id=campaign_id).all()
    return render_template("campaign/view.html", campaign=campaign, ad_requests=ad_requests)
# #--------------------------------------------------------------------------
@app.route('/campaign/<int:id>/edit', methods=['GET', 'POST'])
def edit_campaign(id):
    campaign = Campaign.query.get(id)
    if not campaign:
        flash('Campaign does not exist')
        return redirect(url_for('sponsor_dashboard', sponsor_id=current_user.id))  

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        category = request.form.get('category')
        budget = float(request.form.get('budget'))  
        status = request.form.get('status', 'active')
        visibility = request.form.get('visibility', 'public')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        goal = request.form.get('goal')

        if not name or not category or not budget or not start_date or not end_date:
            flash('Please fill out all required fields')
            return redirect(url_for('edit_campaign', id=id))
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.')
            return redirect(url_for('add_campaign', id=id))

        if start_date > end_date:
            flash('Start date must be before the end date')
            return redirect(url_for('add_campaign', id=id))
        if len(description) > 500:
            flash('Description is too long. Please keep it under 500 characters.')
            return redirect(url_for('add_campaign', id=id))
        try:
            goal = int(goal)
        except ValueError:
            flash('Goal must be a valid number')
            return redirect(url_for('add_campaign', id=id))
        if goal <= 0:
            flash('Goal to reach subscribers cannot be negative')
            return redirect(url_for('add_campaign', id=id))
        if budget < 100 or budget > 1000000:
            flash('Budget must be between 100 and 1,000,000')
            return redirect(url_for('add_campaign', id=id))

        campaign.name = name
        campaign.description = description
        campaign.category = category
        campaign.budget = budget
        campaign.status = status
        campaign.visibility = visibility
        campaign.start_date = start_date
        campaign.end_date = end_date
        campaign.goal = goal

        db.session.commit()

        flash('Campaign updated successfully')
        return redirect(url_for('sponsor_dashboard', sponsor_id=campaign.sponsor_id))
    campaign.start_date = campaign.start_date.strftime('%Y-%m-%d')
    campaign.end_date = campaign.end_date.strftime('%Y-%m-%d')
    return render_template("campaign/edit.html", campaign=campaign,sponsor_id=campaign.sponsor_id)
# #-------------------------------------------------------------------------
@app.route('/campaign/<int:id>/delete', methods=['GET'])
def delete_campaign(id):
    campaign = Campaign.query.get(id)
    if not campaign:
        flash('Campaign not found')
        return redirect(url_for('sponsor_dashboard'))
    return render_template('campaign/delete.html', campaign=campaign)
#--------------------------------------------------------------------------
@app.route('/campaign/<int:id>/delete', methods=['POST'])
def delete_campaign_post(id):
    campaign = Campaign.query.get(id)
    if not campaign:
        flash('Campaign not found')
        return redirect(url_for('sponsor_dashboard'))

    ad_requests = AdRequest.query.filter_by(campaign_id=id).all()
    for ad_request in ad_requests:
        db.session.delete(ad_request)

    db.session.delete(campaign)
    db.session.commit()

    flash('Campaign deleted successfully')
    return redirect(url_for('sponsor_dashboard', sponsor_id=campaign.sponsor_id))
#__________________________________________________________
@app.route('/campaign/<int:id>/<int:sponsor_id>', methods=['GET'])
def adrequest_show_camp(id,sponsor_id):
    campaign = Campaign.query.get(id)
    if not campaign:
        flash('Campaign not found')
        return redirect(url_for('sponsor_dashboard',sponsor_id=sponsor_id))

    ad_requests = campaign.ad_requests
    return render_template('campaign/adrequest_show.html', campaign=campaign, ad_requests=ad_requests,sponsor_id=sponsor_id)
#===========================Adrequest-Add==============================
@app.route('/adrequest/add/<int:campaign_id>/<int:sponsor_id>', methods=['GET', 'POST'])
def add_adrequest(campaign_id,sponsor_id):
    campaign = Campaign.query.get(campaign_id)
    sponsor = User.query.get(sponsor_id)
    if not campaign:
        flash('Campaign not found')
        return redirect(url_for('sponsor_dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        platform_preferences = request.form.get('platform_preferences')
        influencer_id = request.form.get('influencer_id')
        reach = request.form.get('reach')
        payment_amount = request.form.get('payment_amount')
        status = 'pending'
        rating = request.form.get('rating')
        
        if not name or not reach or not payment_amount or not status or not platform_preferences:
            flash('Please fill out all fields')
            return redirect(url_for('add_adrequest', campaign_id=campaign_id))
        try:
            payment_amount = float(payment_amount)
            if payment_amount < 0:
                flash('Payment amount cannot be negative')
                return redirect(url_for('add_adrequest', campaign_id=campaign_id, sponsor_id=sponsor_id))
        except ValueError:
            flash('Invalid payment amount')
            return redirect(url_for('add_adrequest', campaign_id=campaign_id, sponsor_id=sponsor_id))
        try:
            reach = int(reach)
            if reach < 0:
                flash('Reach cannot be negative')
                return redirect(url_for('add_adrequest', campaign_id=campaign_id, sponsor_id=sponsor_id))
        except ValueError:
            flash('Invalid reach value')
            return redirect(url_for('add_adrequest', campaign_id=campaign_id, sponsor_id=sponsor_id))
        if rating:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    flash('Rating must be between 1 and 5')
                    return redirect(url_for('add_adrequest', campaign_id=campaign_id, sponsor_id=sponsor_id))
            except ValueError:
                flash('Invalid rating value')
                return redirect(url_for('add_adrequest', campaign_id=campaign_id, sponsor_id=sponsor_id))
        
        adrequest = AdRequest(
            ad_name=name,
            platform_preferences=platform_preferences,
            campaign_id=campaign_id,  # Use the route parameter directly
            influencer_id=influencer_id,
            reach=int(reach) if reach is not None else 0,
            payment_amount=float(payment_amount) if payment_amount is not None else 0.0,
            ad_status=status, 
            rating=int(rating) if rating else None, 
            sponsor_id=sponsor_id
        )
        db.session.add(adrequest)
        db.session.commit()
        
        if influencer_id:
            request_entry = Request(
                campaign_id=campaign_id,
                influencer_id=influencer_id,
                sponsor_id=sponsor_id,
                request_status=status,
                ad_request_id=adrequest.id
            )
            db.session.add(request_entry)
            db.session.commit()
        flash('Ad request added successfully')
        return redirect(url_for('adrequest_show_camp', id=campaign_id,sponsor_id=sponsor_id))
    
    influencers = User.query.filter_by(role='influencer').all()
    return render_template('adrequest/add.html', campaign=campaign, influencers=influencers,sponsor_id=sponsor_id)
#=================================Adrequest-Edit================================================================
@app.route('/adrequest/<int:id>/edit')
def edit_adrequest(id):
    adrequest = AdRequest.query.get(id)
    if not adrequest:
        flash('Adrequest not found')
        return redirect(url_for('sponsor_dashboard', sponsor_id=adrequest.campaign.sponsor_id))  
    
    campaigns = Campaign.query.all()
    campaign = Campaign.query.get(adrequest.campaign_id)
    influencers = User.query.filter_by(role='influencer').all()
    return render_template('adrequest/edit.html', campaigns=campaigns, adrequest=adrequest, campaign=campaign, influencers=influencers)

@app.route('/adrequest/<int:id>/edit', methods=['POST'])
def edit_adrequest_post(id):
    adrequest = AdRequest.query.get(id)
    if not adrequest:
        flash('Adrequest not found')
        return redirect(url_for('sponsor_dashboard', sponsor_id=adrequest.campaign.sponsor_id))  
    name = request.form.get('name')
    platform_preferences = request.form.get('platform_preferences')
    campaign_id = request.form.get('campaign_id')
    reach = int(request.form['reach']) if request.form['reach'] else None
    payment_amount = float(request.form['payment_amount'])
    status = request.form.get('status')
    rating = int(request.form['rating']) 
    influencer_id = request.form.get("influencer_id")

    if not name or not reach or not payment_amount or not rating or not status:
        flash('Please fill all fields')
        return redirect(url_for('edit_adrequest', id=id))

    if payment_amount <= 0 or (rating is not None and rating <= 0):
        flash('Invalid parameters')
        return redirect(url_for('edit_adrequest', id=id))

    try:
        reach = int(reach)
        payment_amount = float(payment_amount)
        rating = int(rating)
    except ValueError:
        flash('Invalid parameters')
        return redirect(url_for('edit_adrequest', id=id))
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        flash('Invalid campaign')
        return redirect(url_for('edit_adrequest', id=id))

    adrequest = AdRequest.query.get(id)
    if not adrequest:
        flash('Ad request not found')
        return redirect(url_for('edit_adrequest', id=id))

    adrequest.ad_name = name
    adrequest.platform_preferences = platform_preferences
    adrequest.campaign_id = campaign_id  
    adrequest.reach = reach
    adrequest.payment_amount = payment_amount
    adrequest.ad_status = status
    adrequest.rating = rating
    adrequest.influencer_id=influencer_id

    db.session.commit()
    if influencer_id:
                
        request_entry = Request(
                campaign_id=campaign_id,
                influencer_id=influencer_id,
                sponsor_id=adrequest.sponsor_id,
                request_status=status,
                ad_request_id=adrequest.id
            )
        db.session.add(request_entry)
        db.session.commit()
        request_e = Request.query.filter_by(ad_request_id=id,campaign_id=campaign_id,sponsor_id=adrequest.sponsor_id).first()
        if request_e:
            request_e.influencer_id = influencer_id
            request_e.request_status = status
            db.session.commit()
    flash('Ad request updated successfully')
    return redirect(url_for('sponsor_dashboard', sponsor_id=adrequest.campaign.sponsor_id))  
#-------------------------------------Adrequest-Delete----------------------------------------------------------
@app.route('/adrequest/<int:id>/delete')
def delete_adrequest(id):
    adrequest = AdRequest.query.get(id)
    if not adrequest:
        flash('Ad request does not exist')
        return redirect(url_for('sponsor_dashboard'))
    return render_template('adrequest/delete.html', adrequest=adrequest)

@app.route('/adrequest/<int:id>/delete', methods=['POST'])
def delete_adrequest_post(id):
    adrequest = AdRequest.query.get(id)
    if not adrequest:
        flash('Ad request does not exist')
        return redirect(url_for('sponsor_dashboard'))

    sponsor_id = adrequest.campaign.sponsor_id  # Navigate through the relationships to get the sponsor_id
    
    related_requests = Request.query.filter_by(ad_request_id=id).all()
    for request in related_requests:
        db.session.delete(request)
    db.session.delete(adrequest)
    db.session.commit()
    
    flash('Ad request deleted successfully')
    return redirect(url_for('sponsor_dashboard', sponsor_id=sponsor_id))
#==================admin==============
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
@app.route('/admin', methods=['GET'])
def admin_home():
    user_id = session.get('user_id')
    if user_id is None:
        flash("You need to be logged in to access the admin page!")
        return redirect(url_for('home'))

    user = User.query.get(user_id)
    if user is None:
        flash("User not found!")
        return redirect(url_for('home'))

    if not user.is_admin:
        flash("You are not authorized to view this page!")
        return redirect(url_for('home'))
    
    users = User.query.all()
    campaigns = Campaign.query.all()
    public_campaigns = Campaign.query.filter_by(visibility='public').count()
    private_campaigns = Campaign.query.filter_by(visibility='private').count()
    active_users = User.query.count()  
    #ad_request = AdRequest.query.get(id)
    #campaign = Campaign.query.get(id)
    adrequests = AdRequest.query.all()
    sponsors = User.query.filter_by(role='sponsor').all()
    influencers = User.query.filter_by(role='influencer').all()

    total_campaigns = len(campaigns)
    total_ad_requests = len(adrequests)
    flagged_counts = get_flagged_counts()
    bar_chart_data = {
        'labels': [campaign.name for campaign in campaigns],
        'values': [len(campaign.ad_requests) for campaign in campaigns]
    }
    polar_chart_data = {
        'labels': [campaign.name for campaign in campaigns],
        'values': [len(campaign.ad_requests) for campaign in campaigns]
    }
    flagged_counts = get_flagged_counts()
    return render_template('admin_dashboard.html',
                           campaigns=campaigns,
                           public_campaigns=public_campaigns,
                           private_campaigns=private_campaigns,
                           active_users=active_users,
                           adrequests=adrequests,
                           sponsors=sponsors,
                           flagged_counts=flagged_counts,
                           flagged_items=flagged_items,
                           total_ad_requests=total_ad_requests,
                           total_campaigns=total_campaigns,
                           influencers=influencers,users=users,
                           bar_chart_data=bar_chart_data,polar_chart_data=polar_chart_data)
                        
                        
#=========================Admin-View=====================================

@app.route('/admin/campaign/view/<int:id>', methods=['GET'])
def admin_view_campaign(id):
    campaign = Campaign.query.get_or_404(id)
    return render_template('admin/view_details.html', view_type='campaign', campaign=campaign)

@app.route('/admin/influencer/view/<int:id>')
def admin_view_influencer(id):
    influencer = User.query.get_or_404(id)
    return render_template('admin/view_details.html', view_type='influencer', influencer=influencer)

@app.route('/admin/sponsor/view/<int:id>')
def admin_view_sponsor(id):
    sponsor = User.query.get_or_404(id)
    return render_template('admin/view_details.html', view_type='sponsor', sponsor=sponsor)

@app.route('/admin/adrequests/view/<int:id>')
def admin_view_adrequests(id):
    adrequest = AdRequest.query.get_or_404(id)
    return render_template('admin/view_details.html', view_type='adrequest', adrequest=adrequest)


 # #-------admin-sponsors list----------
@app.route('/admin/sponsors', methods=['GET'])
def admin_sponsors_list():
    sponsors = User.query.filter(User.role == 'sponsor').all()
    return render_template('admin_sponsors.html', sponsors=sponsors)

#---admin-inflist--------------   
@app.route('/admin/influencers', methods=['GET'])
def admin_influencers_list():
    influencers = User.query.filter(User.role == 'influencer').all()
    return render_template('admin_influencers.html', influencers=influencers)

@app.route('/admin/adrequests', methods=['GET'])
def admin_adrequests_list():
    adrequests = User.query.all()
    return render_template('admin_adrequests.html', adrequests=adrequests)
    
#================influencer Routes==========================
@app.route('/influencer/dashboard/<int:influencer_id>')
def influencer_dashboard(influencer_id):
    if 'user_id' not in session or session.get('user_role') != 'influencer':
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    influencer = User.query.filter_by(id=influencer_id, role='influencer').first()

    if influencer is None:
        flash('Influencer not found.')
        return redirect(url_for('login')) 
    
    adrequests = AdRequest.query.all()
    payment_amount = request.args.get('payment_amount', '')
    ad_requests = AdRequest.query.filter_by(influencer_id=influencer_id).all()
    active_ad_requests = AdRequest.query.filter_by(influencer_id=influencer_id, ad_status='active').all()
    campaigns = Campaign.query.all()
    
    influencer_campaign_requests = Request.query.filter_by(influencer_id=influencer_id).all()

    if payment_amount:
        try:
            payment_amount = float(payment_amount)
        except ValueError:
            payment_amount = 0.0
            flash('Invalid Payment Amount')
            return redirect(url_for('influencer_dashboard', influencer_id=influencer_id))
        
        if payment_amount <= 0:
            flash('Invalid Payment Amount')
            return redirect(url_for('influencer_dashboard', influencer_id=influencer_id))
    
    return render_template(
        'influencer_dashboard.html',
        name=influencer.username,
        influencer=influencer,
        payment_amount=payment_amount,
        influencer_id=influencer_id,
        adrequests=adrequests,
        ad_requests=ad_requests,
        active_ad_requests=active_ad_requests,
        campaigns=campaigns,
        active_requests=influencer_campaign_requests
    )
#========================inf-view-campaign====
@app.route('/influencer/campaign/view/<int:campaign_id>',methods=['GET'])
def inf_view_campaign(campaign_id):
    user_role = session.get('role')  
    user_id = session.get('user_id')
    influencer_id = session.get('influencer_id')  
    campaign = Campaign.query.get_or_404(campaign_id)
    adrequests = AdRequest.query.filter_by(campaign_id=campaign.id).all()

    if not campaign:
        flash('campaign Does not exist')
        return redirect(url_for('influencer_dashboard',influencer_id=influencer_id))
    
    return render_template(
        'influencer/view.html', 
        campaign=campaign, 
        adrequests=adrequests,
        influencer_id=influencer_id)
#=========================================================

#=================inf-adrequest-view======================
@app.route('/influencer/adrequest/view/<int:adrequest_id>', methods=['GET'])
def inf_adrequest_view(adrequest_id):
    if 'user_id' not in session or session.get('user_role') != 'influencer':
        return redirect(url_for('login'))

    adrequest = AdRequest.query.get(adrequest_id)
    if not adrequest:
        flash('Ad request does not exist or you do not have permission to view it.')
        return redirect(url_for('influencer_dashboard', influencer_id=session.get('user_id')))

    influencer_id = session.get('user_id')
    influencer = User.query.get(influencer_id)
    
    if not influencer:
        flash('Influencer not found.')
        return redirect(url_for('login'))

    return render_template('influencer/ad_view.html', adrequest=adrequest, influencer_id=influencer_id)
#_________user__________________
@app.route('/user/<int:user_id>/delete')

def user_delete(user_id):
    user_to_delete = User.query.get(user_id)

    if not user_to_delete:
        flash("User not found!")
        return redirect(url_for('admin_home'))
    
    # Check if the user is an admin or not
    if user_to_delete.is_admin:
        flash("Cannot delete admin!")
        return redirect(url_for('admin_home'))
    
    # Determine the role of the user and render the appropriate template
    if user_to_delete.role == 'sponsor':
        return render_template('/admin/user_delete.html', user=user_to_delete)
    elif user_to_delete.role == 'influencer':
        return render_template('/admin/user_delete.html', user=user_to_delete)
    else:
        flash("Unknown user role!")
        return redirect(url_for('admin_home'))

@app.route('/user/<int:user_id>/delete', methods=['POST'])
def user_delete_post(user_id):
    user_to_delete = User.query.get(user_id)
    
    if not user_to_delete:
        flash("User not found!")
        return redirect(url_for('admin_home'))
    
    # Check if the user is an admin or not
    if user_to_delete.is_admin:
        flash("Cannot delete admin!")
        return redirect(url_for('admin_home'))
    
    # Delete the user based on their role
    db.session.delete(user_to_delete)
    db.session.commit()
    flash("User deleted successfully!")
    return redirect(url_for('admin_home'))
#===============================Flag=====================================
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

import json
import os

FLAGGED_ITEMS_FILE = 'flagged_items.json'

def load_flagged_items():
    if os.path.exists(FLAGGED_ITEMS_FILE):
        with open(FLAGGED_ITEMS_FILE, 'r') as f:
            return json.load(f)
    return {
        'sponsor': [],
        'influencer': [],
        'campaign': [],
        'ad_request': []
    }

def save_flagged_items(flagged_items):
    with open(FLAGGED_ITEMS_FILE, 'w') as f:
        json.dump(flagged_items, f)

flagged_items = load_flagged_items()


@app.route('/flag_item/<string:item_type>/<int:item_id>', methods=['POST'])
def flag_item(item_type, item_id):
    if item_type == 'sponsor':
        sponsor = User.query.get(item_id)
        if sponsor and sponsor.role == 'sponsor':
            flagged_items['sponsor'].append(sponsor.id)
            # Flag all campaigns by this sponsor
            campaigns = Campaign.query.filter_by(sponsor_id=sponsor.id).all()
            for campaign in campaigns:
                flagged_items['campaign'].append(campaign.id)
                # Flag all ad requests for this campaign
                ad_requests = AdRequest.query.filter_by(campaign_id=campaign.id).all()
                for ad_request in ad_requests:
                    flagged_items['ad_request'].append(ad_request.id)
                    # Flag influencers associated with ad requests
                    influencer = User.query.get(ad_request.influencer_id)
                    if influencer:
                        flagged_items['influencer'].append(influencer.id)
            save_flagged_items(flagged_items)
            flash("Sponsor and related items flagged successfully!")
        else:
            flash("Sponsor not found!")
    elif item_type == 'influencer':
        influencer = User.query.get(item_id)
        if influencer and influencer.role == 'influencer':
            flagged_items['influencer'].append(influencer.id)
            save_flagged_items(flagged_items)
            flash("Influencer flagged successfully!")
        else:
            flash("Influencer not found!")
    elif item_type == 'campaign':
        campaign = Campaign.query.get(item_id)
        if campaign:
            flagged_items['campaign'].append(campaign.id)
            # Flag all ad requests for this campaign
            ad_requests = AdRequest.query.filter_by(campaign_id=campaign.id).all()
            for ad_request in ad_requests:
                flagged_items['ad_request'].append(ad_request.id)
                # Flag influencers associated with ad requests
                influencer = User.query.get(ad_request.influencer_id)
                if influencer:
                    flagged_items['influencer'].append(influencer.id)
            save_flagged_items(flagged_items)
            flash("Campaign and related items flagged successfully!")
        else:
            flash("Campaign not found!")
    elif item_type == 'ad_request':
        ad_request = AdRequest.query.get(item_id)
        if ad_request:
            flagged_items['ad_request'].append(ad_request.id)
            # Flag influencer associated with this ad request
            influencer = User.query.get(ad_request.influencer_id)
            if influencer:
                flagged_items['influencer'].append(influencer.id)
            save_flagged_items(flagged_items)
            flash("Ad request and related items flagged successfully!")
        else:
            flash("Ad request not found!")
    else:
        flash("Invalid item type!")

    return redirect(url_for('admin_home'))

#=======================unflagg=======================================
@app.route('/unflag_item/<string:item_type>/<int:item_id>', methods=['POST'])
def unflag_item(item_type, item_id):
    if item_type == 'sponsor':
        if item_id in flagged_items['sponsor']:
            flagged_items['sponsor'].remove(item_id)
            # Unflag all campaigns by this sponsor
            campaigns = Campaign.query.filter_by(sponsor_id=item_id).all()
            for campaign in campaigns:
                flagged_items['campaign'].remove(campaign.id)
                # Unflag all ad requests for this campaign
                ad_requests = AdRequest.query.filter_by(campaign_id=campaign.id).all()
                for ad_request in ad_requests:
                    flagged_items['ad_request'].remove(ad_request.id)
                    # Unflag influencers associated with ad requests
                    influencer = User.query.get(ad_request.influencer_id)
                    if influencer:
                        flagged_items['influencer'].remove(influencer.id)
            flash("Sponsor and related items unflagged successfully!")
        else:
            flash("Sponsor not found in flagged items!")
    elif item_type == 'influencer':
        if item_id in flagged_items['influencer']:
            flagged_items['influencer'].remove(item_id)
            flash("Influencer unflagged successfully!")
        else:
            flash("Influencer not found in flagged items!")
    elif item_type == 'campaign':
        if item_id in flagged_items['campaign']:
            flagged_items['campaign'].remove(item_id)
            # Unflag all ad requests for this campaign
            ad_requests = AdRequest.query.filter_by(campaign_id=item_id).all()
            for ad_request in ad_requests:
                flagged_items['ad_request'].remove(ad_request.id)
                # Unflag influencers associated with ad requests
                influencer = User.query.get(ad_request.influencer_id)
                if influencer:
                    flagged_items['influencer'].remove(influencer.id)
            flash("Campaign and related items unflagged successfully!")
        else:
            flash("Campaign not found in flagged items!")
    elif item_type == 'ad_request':
        if item_id in flagged_items['ad_request']:
            flagged_items['ad_request'].remove(item_id)
            # Unflag influencer associated with this ad request
            influencer = User.query.get(ad_request.influencer_id)
            if influencer:
                flagged_items['influencer'].remove(influencer.id)
            flash("Ad request and related items unflagged successfully!")
        else:
            flash("Ad request not found in flagged items!")
    else:
        flash("Invalid item type!")

    return redirect(url_for('admin_home'))

   #========================campaign-request=====================================
@app.route('/influencer/request_campaign/<int:influencer_id>/<int:ad_request_id>', methods=['POST'])
def request_campaign(influencer_id, ad_request_id):
    influencer = User.query.get(influencer_id)
    ad_request = AdRequest.query.get(ad_request_id)
    
    if influencer and ad_request:
        ad_request.influencer_id = influencer.id
        ad_request.ad_status = 'pending'
        db.session.commit()
        request = Request.query.filter_by(influencer_id=influencer.id,ad_request_id=ad_request.id).first()
        if request:
            flash("Campaign Request was rejected!")
        
        else:      
            new_influencer_campaign_request = Request(
                campaign_id=ad_request.campaign_id,
                influencer_id=influencer.id,
                sponsor_id=ad_request.sponsor_id,
                ad_request_id=ad_request.id,
                request_status='pending'
            )
            db.session.add(new_influencer_campaign_request)
            db.session.commit()
            flash("Campaign Requested successfully!")  
    else:
        flash("Invalid influencer or ad request.")
    
    return redirect(url_for('influencer_dashboard', influencer_id=influencer_id))
# #========================campaign-request=====================================
@app.route('/add_to_request/<int:campaign_id>/<int:adrequest_id>', methods=['POST'])
def add_to_request(campaign_id,adrequest_id):
    influencer_id = session.get('user_id')  
    campaign = Campaign.query.get(campaign_id)
    
    if not campaign:
        flash('Campaign not found', 'error')
        return redirect(url_for('influencer_dashboard', influencer_id=influencer_id))
    
    # new_request = AdRequest(campaign_id=campaign.id, influencer_id=influencer_id)
    # db.session.add(new_request)
    # db.session.commit()
    request = Request.query.filter_by(influencer_id=influencer_id,ad_request_id=adrequest_id).first()
    if request:
            flash("Campaign Request was rejected!")
    else:  
        new_influencer_campaign_request = Request(
            campaign_id=campaign.id,
            influencer_id=influencer_id,
            sponsor_id=campaign.sponsor_id,
            ad_request_id=adrequest_id,
            request_status='pending'
        )
        db.session.add(new_influencer_campaign_request)
        db.session.commit()
        flash('Request successfully added', 'success')
    return redirect(url_for('influencer_dashboard', influencer_id=influencer_id))
#================influencer-Accept-Reject===========================================
@app.route('/accept_request/<int:adrequest_id>', methods=['POST'])
def accept_request(adrequest_id):
    ad_request = AdRequest.query.get_or_404(adrequest_id)
    print(ad_request)
    ad_request.ad_status = 'accepted'
    db.session.commit()
    if ad_request.ad_status == 'accepted' and ad_request.influencer_id:
        request = Request.query.filter_by(ad_request_id=adrequest_id, influencer_id=ad_request.influencer_id).first()
        if request:
            request.request_status = 'accepted'
            db.session.commit()
    flash('Ad request accepted', 'success')
    return redirect(url_for('influencer_dashboard', influencer_id=ad_request.influencer_id))

@app.route('/reject_request/<int:adrequest_id>', methods=['POST'])
def reject_request(adrequest_id):
    ad_request1 = AdRequest.query.get_or_404(adrequest_id)
    if ad_request1.ad_status == 'pending' or ad_request1.ad_status == 'accepted':
        ad_request1.ad_status = 'rejected'
        
        if ad_request1.influencer_id:
            request = Request.query.filter_by(ad_request_id=adrequest_id, influencer_id=ad_request1.influencer_id).first()
            if request:
                request.request_status = 'rejected'
                db.session.commit()
        influencer_id = ad_request1.influencer_id       
        ad_request1.influencer_id = None
        db.session.commit()
        flash('Ad request rejected', 'success')
        return redirect(url_for('influencer_dashboard', influencer_id=influencer_id))
    if ad_request1.ad_status == 'rejected':
        flash('Ad request already rejected', 'error')
        return redirect(url_for('influencer_dashboard', influencer_id=ad_request1.influencer_id))
    return redirect(url_for('influencer_dashboard', influencer_id=ad_request1.influencer_id))
#+============================Sponsor-search=====================================
@app.route('/search/<int:sponsor_id>', methods=["GET", "POST"])
def search(sponsor_id):
    sponsor = User.query.get(sponsor_id)
    if not sponsor:
        return "Sponsor not found", 404

    if request.method == 'POST':
        search_term = request.form['search_term']
        search_term = f"%{search_term.lower()}%"
        
        if 'search_influencer' in request.form:
            results = User.query.filter(User.role == 'influencer', User.username.ilike(search_term)).all()
        elif 'search_niche' in request.form:
            results = User.query.filter(User.role == 'influencer', User.niche.ilike(search_term)).all()
        else:
            results = []

        return render_template('searchresults_sponsor.html', influencers=results, sponsor=sponsor)
    
    return render_template('search_sponsor.html', sponsor=sponsor)


#===========influencer-search============
@app.route('/search_public_campaigns', methods=['GET', 'POST'])
def search_public_campaigns():
    if request.method == 'POST':
        influencer_id = session.get('user_id')
        if influencer_id is None:
            return redirect(url_for('login'))  # Ensure the user is logged in

        search_term = request.form.get('search_term', '')
        search_category = request.form.get('search_category', '')

        results = Campaign.query.filter(
            Campaign.visibility == 'public',
            Campaign.name.ilike(f'%{search_term}%'),
            Campaign.category.ilike(f'%{search_category}%')
        ).all()
        return render_template('influencer/search_results.html', campaigns=results, influencer_id=influencer_id)
    return render_template('search_form.html')
#=================admin-search===============================
@app.route('/search_results', methods=['GET'])
def search_results():
    search_query = request.args.get('search_query', '').strip().lower()
    filtered_sponsors = User.query.filter(User.role == 'sponsor', User.username.ilike(f'%{search_query}%')).all()
    filtered_influencers = User.query.filter(User.role == 'influencer', User.name.ilike(f'%{search_query}%')).all()
    filtered_campaigns = Campaign.query.filter(Campaign.name.ilike(f'%{search_query}%')).all()
    filtered_adrequests = AdRequest.query.filter(AdRequest.ad_name.ilike(f'%{search_query}%')).all()

    return render_template('admin/search_results.html',
                           search_query=search_query,
                           filtered_sponsors=filtered_sponsors,
                           filtered_influencers=filtered_influencers,
                           filtered_campaigns=filtered_campaigns,
                           filtered_adrequests=filtered_adrequests)
#--------------------------------------------------------------------------------
@app.route('/accept_ad_request/<int:request_id>', methods=['POST'])
def accept_ad_request(request_id):
    ad_request = AdRequest.query.get_or_404(request_id)
    ad_request.ad_status = 'accepted'
    
    campaign_request = Request.query.filter_by(ad_request_id=request_id).first()
    if campaign_request:
        campaign_request.request_status = 'accepted'
    
    db.session.commit()
    flash('Ad request accepted successfully!', 'success')
    return redirect(url_for('sponsor_dashboard', sponsor_id=ad_request.sponsor_id))

@app.route('/reject_ad_request/<int:request_id>', methods=['POST'])
def reject_ad_request(request_id):
    ad_request = AdRequest.query.get_or_404(request_id)
    ad_request.ad_status = 'rejected'
    
    campaign_request = Request.query.filter_by(ad_request_id=request_id).first()
    if campaign_request:
        campaign_request.request_status = 'rejected'
    
    db.session.commit()
    flash('Ad request rejected successfully!', 'success')
    return redirect(url_for('sponsor_dashboard', sponsor_id=ad_request.sponsor_id))