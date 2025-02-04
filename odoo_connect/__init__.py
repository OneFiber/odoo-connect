import logging
import urllib.parse
from typing import Dict, Optional

from .odoo_rpc import OdooClient, OdooModel, OdooServerError  # noqa

__doc__ = """Simple Odoo RPC library."""


class OdooConnectionError(OdooServerError):
    """Connection error"""

    pass


def connect(
    url: str,
    database: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    infer_parameters: bool = True,
    check_connection: bool = True,
    context: Optional[Dict] = None,
    monodb: bool = False,
    **kw,
) -> OdooClient:
    """Connect to an odoo database.

    When infer_paramters is set, the url is parsed to get additional information.
    - When missing, the scheme is https (or http on localhost)
    - When missing we try the following heuristics: the database is read from the path,
      in a multipart host name, the first part is used, otherwise a default database
    - The username and password are read if present in the url
    - When missing, the password is copied from the user

    Some examples for infered parameters:
    - https://user:pwd@hostname/database
    - mytest.dev.odoo.com -> https://mytest.dev.odoo.com/mytest
    - https://admin@myserver:8069 would connect with password "admin" to the default database

    :param url: The URL to the server, it may encode other information when infer_parameters is set
    :param database: The database name (optional)
    :param username: The username (when set, we try to authenticate the user during the connection)
    :param password: The password
    :param infer_paramters: Whether to infer parameters (default: True)
    :param check_connection: Try to connect (default: True)
    :param monodb: Allow for a db.monodb call to find the default database
           (default: set when database == "@monodb")
    :return: Connection object to the Odoo instance
    """
    if kw:
        logging.warning('Unknown connect() paramters: %s', list(kw.keys()))
    if database == '@monodb':
        monodb = True
        database = None
    urlx = urllib.parse.urlparse(url)
    if infer_parameters:
        if not urlx.scheme and not urlx.netloc and urlx.path:
            # we just have a server name in the path (reparse with slashes)
            urlx = urllib.parse.urlparse('//' + urlx.path.lstrip('/'))
        if not urlx.hostname:
            raise ValueError(f"No hostname in url {url}")
        if not database and len(urlx.path) > 1:
            # extract the database from the path if it's there
            path = urlx.path.lstrip('/')
            if '/' not in path:
                database = path
                urlx = urlx._replace(path='/')
        if not database:
            # try to extract the database from the hostname
            # dbname.runbot*.odoo.com or dbname.dev.odoo.com
            # except IP addresses
            name_split = (urlx.hostname or '').split('.')
            if len(name_split) > 3 and not name_split[-1].isnumeric():
                database = name_split[0]
        if not username and urlx.username:
            # read username and password from the url
            username = urlx.username
            password = urlx.password
        if not password and username:
            # copy username to password when not set
            password = username
        # make sure the url does not contain credentials anymore
        at_loc = urlx.netloc.find('@')
        if at_loc > 0:
            urlx = urlx._replace(netloc=urlx.netloc[at_loc + 1 :])
    if not urlx.scheme:
        # add a scheme
        urlx = urlx._replace(scheme="http" if urlx.hostname == "localhost" else "https")
    url = urlx.geturl()

    # Create the connection
    try:
        client = OdooClient(url=url, database=database or 'odoo')
        if not database:
            database = client._find_default_database(monodb=monodb)
            check_connection = database == 'odoo'  # check if it's the default database
            client.database = database
        if context:
            client.context.update(context)
        if username:
            client.authenticate(username, password or '')
        elif check_connection:
            client.version()
        return client
    except (NotImplementedError, OdooConnectionError):
        raise
    except (ConnectionError, IOError, OdooServerError) as e:
        raise OdooConnectionError(e)

__all__ = [
    "connect",
    "OdooConnectionError",
    "OdooClient",
    "OdooModel",
    "OdooServerError",    
]
