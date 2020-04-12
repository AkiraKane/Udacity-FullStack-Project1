#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
import sys
import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import phonenumbers
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from wtforms import ValidationError
from forms import *
from flask_migrate import Migrate
from datetime import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column("genres", db.ARRAY(db.String()), nullable=False)
    website = db.Column(db.String(500)) 
    seeking_talent = db.Column(db.Boolean, default=True) 
    seeking_description = db.Column(db.String(500)) 
    shows = db.relationship("Show", backref="venue", lazy=True)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column("genres", db.ARRAY(db.String()), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(500)) 
    seeking_venue = db.Column(db.Boolean, default=True) 
    seeking_description = db.Column(db.String(500)) 
    shows = db.relationship("Show", backref="artist", lazy=True)

class Show(db.Model):
  __tablename__ = "Show"
  id = db.Column(db.Integer, primary_key=True)
  venue_id = db.Column(db.Integer, db.ForeignKey("Venue.id"), nullable=False)
  artist_id = db.Column(db.Integer, db.ForeignKey("Artist.id"), nullable=False)
  start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

# used for formatting user time input
def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

# validates user phone numbers
def phone_validator(num):
    parsed = phonenumbers.parse(num, "US")
    if not phonenumbers.is_valid_number(parsed):
        raise ValidationError('Must be a valid US phone number.')

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():

  # define a list to store venues data
  data = []

  # retrieve all venues data from database as a list
  venues = Venue.query.all()

  # only add unique combinations of city and state in a set
  venues_locations = set()
  for venue in venues:
    venues_locations.add([venue.city, venue.state])
  
  # structure out of the data list by iterating each combo
  for location in venues_locations:
    data.append({
      "city": location[0],
      "state": location[1],
      "venues": []
    })

  # iterating each venue, then get the # of upcoming shows from Show table
  for venue in venues:
    num_upcoming_shows = 0

    # filter Show table corresponding venue id, output as a list 
    shows = Show.query.filter_by(venue_id = venue.id).all()

    # if the start time is after today, add 1 
    for show in shows:
      if show.start_time > datetime.now():
        num_upcoming_shows += 1
    
    # for each item in data, add venues to match city/state
    for item in data:
      if venue.city == item["city"] and venue.state == item["state"]:
        item["venues"].append({
          "id": venue.id,
          "name": venue.name,
          "num_upcoming_shows": num_upcoming_shows
        })
  
  # render venues page with data
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # Get the search term from user
  search_term=request.form.get('search_term', '')

  # find all matching venues based on search term
  # including partial match and case insensitive
  venues = Venue.query.fliter(Venue.name.ilike(f"%{search_term}%")).all()

  response = {
    "count": len(venues),
    "data": []
  }

  for venue in venues:
    num_upcoming_shows = 0

    # filter Show table corresponding venue id, output as a list 
    shows = Show.query.filter_by(venue_id = venue.id).all()

    # if the start time is after today, add 1 
    for show in shows:
      if show.start_time > datetime.now():
        num_upcoming_shows += 1

    # add data values to response
    response["data"].append({
      "id": venue.id,
      "name": venue.name,
      "num_upcoming_shows": num_upcoming_shows
      })

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # get the venue corresponding to the user input venue id
  venue = Venue.query.filter_by(id = venue_id).first()

  # get all the shows records for a given venue id
  shows = Show.query.filter_by(venue_id = venue_id).all()

  # return upcoming shows
  def upcoming_shows_func():
    upcoming_shows = []

    for show in shows:
      if show.start_time > datetime.now():
        upcoming_shows.append({
          "artist_id": show.artist_id,
          "artist_name": Artist.query.filter_by(id = show.artist_id).first().name,
          "artist_image_link": Artist.query.filter_by(id = show.artist_id).first().image_link,
          "start_time": format_datetime(str(show.start_time)) 
        })
    return upcoming_shows
  
  # return past shows
  def past_shows_func():
    past_shows = []

    for show in shows:
      if show.start_time <= datetime.now():
        past_shows.append({
          "artist_id": show.artist_id,
          "artist_name": Artist.query.filter_by(id = show.artist_id).first().name,
          "artist_image_link": Artist.query.filter_by(id = show.artist_id).first().image_link,
          "start_time": format_datetime(str(show.start_time)) 
        })
    return past_shows
  
  # populate data
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres,
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows_func(),
    "upcoming_shows": upcoming_shows_func(),
    "past_shows_count": len(past_shows_func()),
    "upcoming_shows_count": len(upcoming_shows_func())
  }
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():

  try:
    # load form data from user inpit on submit
    form = VenueForm()
    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    phone = form.phone.data
    phone_validator(phone)
    genres = form.genres.data
    facebook_link = form.facebook_link.data
    website = form.website.data
    image_link = form.image_link.data
    seeking_talent = True if form.seeking_talent.data == 'Yes' else False
    seeking_description = form.seeking_description.data

    # create new Venue
    venue = Venue(name=name, city=city, state=state, address=address,
                  phone=phone, genres=genres, facebook_link=facebook_link,
                  website=website, image_link=image_link,
                  seeking_talent=seeking_talent,
                  seeking_description=seeking_description)

    # add new venue to session and commit to database
    db.session.add(venue)
    db.session.commit()

    # on successful db insert, flash success
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  
  except ValidationError as e:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed. ' + str(e))

  except:
    # catches all other exceptions
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')

  finally:
    # always close the session
    db.session.close()

  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    # get the venue corresponding to the user input venue id
    venue = Venue.query.filter_by(id = venue_id).first()

    name = venue.name

    db.session.delete(venue)
    db.session.commit()

    # on successful db delete, flash success
    flash("Venue " + name + " was successfully deleted")

  except:
    print("Oops!", sys.exc_info()[0], "occured")
    db.session.rollback()
    flash("An error occurred. Venue " + name + " could not be deleted")
  
  finally:
    db.session.close()

  return jsonify({"success": True})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  # get all the artists
  artists = Artist.query.all()
  
  data = []

  for artist in artists:
    data.append({
      "id": artist.id,
      "name": artist.name
    })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():

  # get the search term from user input
  search_term=request.form.get('search_term', '')

  # get all the artists based on the user input and including partial match and case-insensitive
  artists = Artist.query.filter(Artist.name.ilike(f"%{search_term}%")).all()

  response = {
    "count": len(artists),
    "data": []
  }

  # get the # of upcoming shows and update the data
  for artist in artists:
    num_upcoming_shows = 0

    shows = Show.query.filter_by(artist_id = artist.id).all()

    for show in shows:
      if show.start_time > datetime.now():
        num_upcoming_shows += 1
    
    response["data"].append({
      "id": artist.id,
      "name": artist.name,
      "num_upcoming_shows": num_upcoming_shows
    })

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  # get artist based on given artist id
  artist = Artist.query.filter_by(id = artist_id).first()

  # get all shows based on given artist id 
  shows = Show.query.filter_by(artist_id = artist_id).all()

  # return upcoming shows for the given artist
  def upcoming_shows_func():
    upcoming_shows = []

    for show in shows:
      if show.start_time > datetime.now():
        venue = Venue.query.filter_by(id = show.venue_id).first()
        upcoming_shows.append({
          "venue_id": show.venue_id,
          "venue_name": venue.name,
          "venue_image_link": venue.image_link,
          "start_time": format_datetime(str(show.start_time))
        })
    return upcoming_shows
  
  # return past shows for the given artist
  def past_shows_func():
    past_shows = []

    for show in shows:
      if show.start_time <= datetime.now():
        venue = Venue.query.filter_by(id = show.venue_id).first()
        past_shows.append({
          "venue_id": show.venue_id,
          "venue_name": venue.name,
          "venue_image_link": venue.image_link,
          "start_time": format_datetime(str(show.start_time))
        })
    return past_shows
  
  # populate artist data
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres,
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows_func(),
    "upcoming_shows": upcoming_shows_func(),
    "past_shows_count": len(past_shows_func()),
    "upcoming_shows_count": len(upcoming_shows_func()),
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()

  # get the matching artist by id
  artist = Artist.query.filter_by(id=artist_id).first()

  # artist data
  artist = {
      "id": artist.id,
      "name": artist.name,
      "genres": artist.genres,
      "city": artist.city,
      "state": artist.state,
      "phone": artist.phone,
      "website": artist.website,
      "facebook_link": artist.facebook_link,
      "seeking_venue": artist.seeking_venue,
      "seeking_description": artist.seeking_description,
      "image_link": artist.image_link
  }

  # set placeholders in form SelectField dropdown menus to current data
  form.state.process_data(artist['state'])
  form.genres.process_data(artist['genres'])
  form.seeking_venue.process_data(artist['seeking_venue'])

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  try:
    form = ArtistForm()

    # get the current artist by id
    artist = Artist.query.filter_by(id=artist_id).first()

    # load data from user input on form submit
    artist.name = form.name.data
    artist.genres = form.genres.data
    artist.city = form.city.data
    artist.state = form.state.data
    artist.phone = form.phone.data
    phone_validator(artist.phone)
    artist.facebook_link = form.facebook_link.data
    artist.image_link = form.image_link.data
    artist.website = form.website.data
    artist.seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    artist.seeking_description = form.seeking_description.data

    # commit the changes
    db.session.commit()

    flash('Artist ' + request.form['name'] + ' was successfully updated!')
  except ValidationError as e:
      db.session.rollback()
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be listed. ' + str(e))
  except:
      db.session.rollback()
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be updated.')
  finally:
      db.session.close()

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  
  # get the venue by id
  venue = Venue.query.filter_by(id=venue_id).first()

  # load venue data
  venue = {
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres,
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_talent,
      "seeking_description": venue.seeking_description,
      "image_link": venue.image_link
  }

  # set placeholders in form SelectField dropdown menus to current data
  form.state.process_data(venue['state'])
  form.genres.process_data(venue['genres'])
  form.seeking_talent.process_data(venue['seeking_talent'])

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  try:
    form = VenueForm()

    # get the current artist by id
    venue = Venue.query.filter_by(id=venue_id).first()

    # load data from user input on form submit
    venue.name = form.name.data
    venue.genres = form.genres.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.address = form.address.data
    venue.phone = form.phone.data
    phone_validator(venue.phone)
    venue.facebook_link = form.facebook_link.data
    venue.website = form.website.data
    venue.image_link = form.image_link.data
    venue.seeking_talent = True if form.seeking_talent.data == 'Yes' else False
    venue.seeking_description = form.seeking_description.data

    # commit the changes
    db.session.commit()

    flash('Venue ' + request.form['name'] + ' was successfully updated!')
  except ValidationError as e:
      db.session.rollback()
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be listed. ' + str(e))
  except:
      db.session.rollback()
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be updated.')
  finally:
      db.session.close()

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  try:
    form = ArtistForm()

    # load data from user input on form submit
    name = form.name.data
    genres = form.genres.data
    city = form.city.data
    state = form.state.data
    phone = form.phone.data
    phone_validator(phone)
    facebook_link = form.facebook_link.data
    image_link = form.image_link.data
    website = form.website.data
    seeking_venue = True if form.seeking_venue.data == 'Yes' else False
    seeking_description = form.seeking_description.data

    artist = Artist(name=name, city=city, state=state, phone=phone,
                    genres=genres, facebook_link=facebook_link,
                    website=website, image_link=image_link,
                    seeking_venue=seeking_venue,
                    seeking_description=seeking_description)

    # add new data and commit the changes
    db.session.add(artist)
    db.session.commit()

    flash('Artist ' + request.form['name'] + ' was successfully updated!')

  except ValidationError as e:
      db.session.rollback()
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be listed. ' + str(e))
  except:
      db.session.rollback()
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be updated.')
  finally:
      db.session.close()
  
  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  
  # get all the show data
  shows = Show.query.all()

  data = []

  for show in shows:
    venue = Venue.query.filter_by(id = show.venue_id).first()
    artist = Artist.query.filter_by(id = show.artist_id).first()
    data.append({
          "venue_id": show.venue_id,
          "venue_name": venue.name,
          "artist_id": show.artist_id,
          "artist_name": artist.name,
          "artist_image_link": artist.image_link,
          "start_time": format_datetime(str(show.start_time))
    })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  try:
    # get user input data from form
    artist_id = request.form['artist_id']
    venue_id = request.form['venue_id']
    start_time = request.form['start_time']

    # create new show with user data
    show = Show(artist_id=artist_id, venue_id=venue_id,
                start_time=start_time)

    # add show and commit session
    db.session.add(show)
    db.session.commit()

    # on successful db insert, flash success
    flash('Show was successfully listed!')
  except:
      # rollback if exception
      db.session.rollback()

      flash('An error occurred. Show could not be listed.')
  finally:
      db.session.close()
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
