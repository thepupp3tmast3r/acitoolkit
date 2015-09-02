################################################################################
################################################################################
#                                                                              #
# Copyright (c) 2015 Cisco Systems                                             #
# All Rights Reserved.                                                         #
#                                                                              #
#    Licensed under the Apache License, Version 2.0 (the "License"); you may   #
#    not use this file except in compliance with the License. You may obtain   #
#    a copy of the License at                                                  #
#                                                                              #
#         http://www.apache.org/licenses/LICENSE-2.0                           #
#                                                                              #
#    Unless required by applicable law or agreed to in writing, software       #
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT #
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the  #
#    License for the specific language governing permissions and limitations   #
#    under the License.                                                        #
#                                                                              #
################################################################################
"""
Reports: ACI Toolkit report GUI.
"""
from flask import Flask, session, redirect, url_for, jsonify
from flask import flash
from flask.ext import admin
from flask.ext.admin import BaseView, AdminIndexView, expose
from flask.ext.admin.actions import action
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.admin.model.template import macro
from flask.ext.bootstrap import Bootstrap
from flask.ext.wtf import Form, CsrfProtect
from wtforms import SubmitField, StringField, BooleanField
from wtforms import SelectField
from wtforms.validators import Required
from acitoolkit.acitoolkitlib import Credentials
from requests import Timeout, ConnectionError
# Create application
from Forms import FeedbackForm, CredentialsForm, ResetForm
from aciSearchDb import LoginError, SearchDb

# start the flask application and tell it the static folder is called 'static'
app = Flask(__name__, static_folder='static')

# todo: need to validate the secrete key
app.config['SECRET_KEY'] = 'Dnit7qz7mfcP0YuelDrF8vLFvk0snhwP'
app.config['CSRF_ENABLED'] = True
CsrfProtect(app)

bootstrap = Bootstrap(app)

# Create the ACI Search Database
sdb = SearchDb()

class APICArgs(object):
    """
    Class to hold the Arguments of the APIC
    """
    def __init__(self, ipaddr, username, secure, password):
        self.login = username
        self.password = password
        if ipaddr is not None:
            if secure is True:
                self.url = 'https://' + ipaddr
            else:
                self.url = 'http://' + ipaddr
        else:
            self.url = None
        self.modified = True  # flag to indicate that the credentials have changed


class Feedback(BaseView):
    """
    form to allow the user to provide feedback.
    """
    @expose('/')
    def index(self):
        """
        Get feedback

        :return:
        """
        form = FeedbackForm()
        return self.render('feedback.html', form=form)


class SearchBar(Form):
    """
    Base form for showing the select switch form.  List of switches and list of reports.
    """
    search_field = StringField('Search:', validators=[Required()])
    reload = BooleanField('Reload fabric info', validators=[])
    submit = SubmitField('Search')

class SelectSwitchView(BaseView):
    """
    The actual select switch page generator.
    """
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        """
        Allow user to select which report to show.

        :return:
        """
        form = SearchBar()
        report = {}
        if form.validate_on_submit() and form.submit.data:

            # load data from APIC if requested
            if form.data['reload']:
                print 'reload'
                apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
                sdb.set_login_credentials(apic_args)
                sdb.load_db(force_reload=True)

            # load data from file if it has not been otherwise loaded
            if sdb.by_key == {}:
                sdb.load_db()

            # report = DynamicTableForm()
            try:
                report = sdb.get_search_result(form.data['search_field'])
            except Timeout:
                flash('Connection timeout when trying to reach the APIC', 'error')
                return redirect(url_for('switchreportadmin.index_view'))
            except LoginError:
                flash('Unable to login to the APIC', 'error')
                return redirect(url_for('credentialsview.index'))
            except ConnectionError:
                flash('Connection failure.  Perhaps \'secure\' setting is wrong')
                return redirect(url_for('credentialsview.index'))
        if report != {}:
            return self.render('search_result.html', form=form, report=report)
        else:
            return self.render('search_result.html', form=form)


class About(BaseView):
    """
    Displays the about information
    """
    @expose('/')
    def index(self):
        """
        Show about information

        :return:
        """
        return self.render('about.html')


class CredentialsView(BaseView):
    """
    Gets the APIC credentials from the user.
    """
    @expose('/', methods=['GET', 'POST'])
    def index(self):
        """
        Prompt user for APIC credentials

        :return:
        """
        form = CredentialsForm()
        reset_form = ResetForm()
        if session.get('ipaddr') is None:
            session['ipaddr'] = None
            session['secure'] = None
            session['username'] = None
            session['password'] = None

        apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
        sdb.set_login_credentials(apic_args)
        if form.validate_on_submit() and form.submit.data:
            old_ipaddr = session.get('ipaddr')
            old_username = session.get('username')
            old_secure = session.get('secure')
            old_password = session.get('password')
            if ((old_ipaddr is not None and old_ipaddr != form.ipaddr.data) or
                 (old_username is not None and old_username != form.username.data) or
                 (old_secure is not None and old_secure != form.secure.data) or
                 (old_password is not None and old_password != form.password.data)):
                flash('APIC Credentials have been updated')
            session['ipaddr'] = form.ipaddr.data
            session['secure'] = form.secure.data
            session['username'] = form.username.data
            session['password'] = form.password.data
            apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
            sdb.set_login_credentials(apic_args)
            return redirect(url_for('credentialsview.index'))
        elif reset_form.reset.data:
            session['ipaddr'] = None
            session['secure'] = None
            session['username'] = None
            session['password'] = None
            apic_args = APICArgs(session['ipaddr'], session['username'], session['secure'], session['password'])
            sdb.set_login_credentials(apic_args)
            return redirect(url_for('credentialsview.index'))
        return self.render('credentials.html', form=form,
                           reset_form=reset_form,
                           ipaddr=session.get('ipaddr'),
                           username=session.get('username'),
                           security=session.get('secure', 'False'))


# Customized admin interface
# class CustomView(ModelView):
#     """
#     Custom view placeholder class
#     """
#     list_template = 'list.html'



# Create admin with custom base template
homepage_view = AdminIndexView(name='Home', template='admin/index.html',
                               url='/')
admin = admin.Admin(app,
                    name='Search Tom View',
                    index_view=homepage_view,
                    base_template='layout.html')

# Add views
admin.add_view(CredentialsView(name='Credentials'))
admin.add_view(About(name='About' , endpoint='test1', category='Test'))
admin.add_view(About(name='About', endpoint='test2', category='Test'))
admin.add_view(About(name='About 3', endpoint='test3', category='Test'))
admin.add_view(Feedback(name='Feedback'))
admin.add_view(SelectSwitchView(name='Switch Search'))

if __name__ == '__main__':
    description = 'ACI Search Viewer Tool.'
    creds = Credentials('server', description)
    creds.add_argument('--force',
                       action="store_true",
                       default=False,
                       help='Force a rebuild of the search index')
    args = creds.get()
    #sdb.load_db(args.force)
    # Start app
    app.run(debug=True, host=args.ip, port=int(args.port))
