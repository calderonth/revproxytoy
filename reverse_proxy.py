import configparser
import logging
from os import getenv
from sys import exit
import tornado.ioloop
import tornado.gen
import tornado.web
import tornado.httpclient


class MainHandler(tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def initialize(self, config):
        self.config = config

    @tornado.gen.coroutine
    def prepare(self):
        self.host = self.request.headers['Host']
        if not self.host in self.config.sections():
            self.send_error(404)
            return
        if self.request.method not in self.config[self.host]['allowed_methods'].split(','):
            logging.warning("Tried to call using a forbidden method")
            self.send_error(403)
            return
        self.reverse_host = self.config[self.host]['origin']

    @tornado.gen.coroutine
    def _handle_request(self):
        #Rebuilding URL
        self.request.headers['Host'] = self.reverse_host
        url = u"{proto}://{host}{port}{path}{query}"
        url = url.format(
            proto=self.request.protocol,
            host=self.reverse_host,
            port=u'',
            path=u'/'+self.request.path.lstrip(u'/') if self.request.path else u'',
            query=u'?'+self.request.query.lstrip(u'?') if self.request.query else u''
        )
        logging.warning("Handling request for client %s" % str(self.request.remote_ip))
        if "add_forwarded_for" in self.config[self.host].keys():
            self.request.headers['X-Forwarded-For'] = self.request.remote_ip
        req = tornado.httpclient.HTTPRequest(
            url=url,
            method=self.request.method,
            body=self.request.body if self.request.method == "POST" else None,
            headers=self.request.headers
        )
        http_client = tornado.httpclient.AsyncHTTPClient()
        try:
            response = yield http_client.fetch(req)
            self.write(response.body)
        except tornado.httpclient.HTTPClientError as e:
            logging.error("Something went wrong fetching URL, %s" %str(e))
            self.send_error(e.response.code)
        except Exception as e:
            # Other errors are possible, such as IOError.
            logging.error("Error: %s" % str(e))
            self.send_error()

    @tornado.gen.coroutine
    def get(self):
        yield self._handle_request()

    @tornado.gen.coroutine
    def post(self):
        yield self._handle_request()

    @tornado.gen.coroutine
    def put(self):
        yield self._handle_request()

    @tornado.gen.coroutine
    def delete(self):
        yield self._handle_request()

    @tornado.gen.coroutine
    def head(self):
        yield self._handle_request()


def load_config(config_name):
    config = configparser.ConfigParser()
    config.read(config_name)
    logging.warning("Loading %s" % config_name)
    if not config.sections():
        logging.error("Configuration is empty")
        exit(-1)
    for c in config.sections():
        if not "origin" in config[c].keys():
            logging.error("Missing origin_server in %s" % c)
            exit(-1)
        if not "allowed_methods" in config[c].keys():
            logging.error("Missing allowed_methods in %s" % c)
            exit(-1)
        logging.warning("Found mapping %s -> %s, allowed_methods %s" %
            (
                config[c],
                config[c]['origin'],
                config[c]['allowed_methods'].split(',')
            )
        )
        if "add_forwarded_for" in config[c].keys():
            logging.warning("will append X-Forwarded-for")
    return config


def make_app():
    config = load_config(
            getenv('PROXY_CONFIG', "config.ini")
            )
    return tornado.web.Application([
        (r".*", MainHandler, dict(config=config)),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()
