import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    #secret key
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'A-VERY-LONG-SECRET-KEY'
    
    #RECAPTCHA_PUBLIC_KEY
    RECAPTCHA_PUBLIC_KEY = '6LdKjsUhAAAAAAuKEC-Fz3slFIXvFPaqxRgcbSJA'
    #RECAPTCHA_PRIVATE_KEY
    RECAPTCHA_PRIVATE_KEY = '6LdKjsUhAAAAAF57CRRDFZNFzzYySaIUzeYkCC3L'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
