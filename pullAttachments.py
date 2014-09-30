import json, urllib, urllib2, urlparse
import os, shutil
import time
import imghdr


### REST functions

def check_service(service_url):
    components = os.path.split(service_url)
    if service_url == None:
        return True
    elif components[-1].isdigit() :
        return "Layer"
    elif components[-1] == "FeatureServer":
        return "FeatureServer"
    else:
        return False

def get_service_url(layer_url):
    components = os.path.split(layer_url)
    if components[1] == "FeatureServer":
        return layer_url
    else:
        return components[0]

def get_response(url, query='', get_json=True):
    encoded = urllib.urlencode(query)
    request = urllib2.Request(url, encoded)
    if get_json:
        return json.loads(urllib2.urlopen(request).read())
    return urllib2.urlopen(request).read()

def add_path(url, path):
    return urlparse.urljoin(url + "/", path)

def login (username, password):
    CREDENTIALS['username'] = username
    CREDENTIALS['password'] = password
    response = get_response(TOKEN_URL, CREDENTIALS)
    if 'error' in response:
        print response['error']
        exit()
    else:
        return response['token']

def get_fs_name(input_url, token):
    return get_response(input_url,
        {'f':'json', 'token':token})['layers'][0]['name']

def query_id_or_field(url, query, field=None):
    if field:
        query['outFields'] = field
        return get_response(url, query)['features']
    query['returnIdsOnly'] = 'true'
    return get_response(url, query)['objectIds']

### OS functions

def create_and_set_dir(directory_name):
    new_dir = os.path.join(os.getcwd(), directory_name)
    os.makedirs(directory_name)
    os.chdir(directory_name)
    return new_dir

def pull_to_local(url, name, destination, file_format = ''):
    if destination:
        os.chdir(destination)
    if format:
        output = open(str(name) + '.{}'.format(file_format), 'wb')
    else:
        output = open(str(name), 'wb')
    output.write(url)
    output.close()

def group_photos(root_directory, new_directory):
    os.chdir(root_directory)
    photos = [(os.path.join(directory, filename), filename) for directory,
              dirnames, files in os.walk(root_directory) for filename in files if imghdr.what(os.path.join(directory,filename))]
    directory_path = create_and_set_dir(new_directory)
    for photo in photos:
        shutil.copy2(photo[0], os.path.join(directory_path, photo[1]))

### Queries

CREDENTIALS = {
    'username': '',
    'password': '',
    'expiration': '60',
    'client': 'referer',
    'referer': 'www.arcgis.com',
    'f': 'json'
}

TOKEN_URL = "https://www.arcgis.com/sharing/rest/generateToken"

ATTACHMENTS = {
    'where': '1=1',
    'token': '',
    'f': 'json'
}

REPLICA = {
    "geometry": '',
    "geometryType": "esriGeometryEnvelope",
    "inSR": '',
    "layerQueries": '',
    "layers": "0",
    "replicaName": "read_only_rep",
    "returnAttachments": 'false',
    "returnAttachmentsDataByUrl": 'true',
    "transportType": "esriTransportTypeEmbedded",
    "async": 'false',
    "syncModel": "none",
    "dataFormat": "filegdb",
    "token": '',
    "replicaOptions": '',
    "f": "json"
}


class App(object):
    ''' Class with methods to perform tasks with ESRI's REST service '''
    def __init__ (self, input_url, token, destination):
        self.input_url = input_url
        self.token = token
        self.destination = destination
        self.fs_url = get_service_url(input_url)
        self.layer_url = None

    def check_input_url(self):
        input_type = check_service(self.input_url)
        if input_type == "Layer":
            self.layer_url = self.input_url
        if input_type == "FeatureServer":
            self.layer_url = add_path(self.input_url, "0/query")


    def pull_attachments(self, query, field=None):
        query['token'] = self.token
        self.check_input_url()
        feature_ids = query_id_or_field(self.layer_url, query, field)
        os.chdir(self.destination)
        root_name = time.strftime("%Y_%m_%d_") + get_fs_name(self.input_url,
            self.token) + "_Photos"
        root_file = create_and_set_dir(root_name)
        for feature in feature_ids:
            os.chdir(root_file)
            img_url = add_path(self.input_url,
                "0/{}/attachments").format(feature)
            attachments = get_response(img_url, query)['attachmentInfos']
            if len(attachments) > 0:
                create_and_set_dir(str(feature))
                for attachment in attachments:
                    attachment_url = add_path(img_url,
                        "{}/download".format(attachment['id']))
                    attachment_file = get_response(attachment_url,
                        {'token':self.token},
                        get_json = False)
                    pull_to_local(attachment_file, attachment['id'],
                        '', 'jpg')
        group_photos(root_file, "ALL")

    def pull_replica(self, query):
        query['token'] = self.token
        replica_url = add_path(self.fs_url, "createReplica")
        zip_url = get_response(replica_url, query)['responseUrl']
        zip_file = get_response(zip_url, get_json=False)
        file_name = time.strftime("%Y_%m_%d_") + get_fs_name(self.token,
            self.fs_url)
        pull_to_local(zip_file, file_name, self.destination, 'zip')


if __name__ == "__main__":
    TOKEN = login("", "")
    INPUT_URL = ""
    DEST = r""
    RUN = App(INPUT_URL, TOKEN, DEST)
    RUN.pull_replica(REPLICA)
    RUN.pull_attachments(ATTACHMENTS)

