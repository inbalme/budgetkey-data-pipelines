import datetime
import json
import requests
import logging
import time

from datapackage_pipelines.utilities.resources import PROP_STREAMING
from datapackage_pipelines.wrapper import ingest, spew


def ranges(div):
    period = 365*86400/div
    start = datetime.datetime.utcfromtimestamp(0)
    ret = []
    while start.year == 1970:
        end = start + datetime.timedelta(seconds=period)
        if end.year > 1970:
            end = datetime.datetime(year=1970,month=12,day=31)
        else:
            end = datetime.datetime(year=end.year,month=end.month, day=end.day)
        ret.append((
            start.strftime('%m/%d'),
            end.strftime('%m/%d'),
        ))
        start = end + datetime.timedelta(days=1)
    return ret


class GetTransactions(object):

    def requests_post(self, url, data):
        return requests.post(url, data=data).json()

    def get_for_range(self, cid, year_start, range_start, year_end, range_end):
        logging.info('%r %s/%s -> %s/%s', cid, year_start, range_start, year_end, range_end)
        data = {"PartyID": None,
                "EntityID": cid,
                "EntityTypeID": 1,
                "PublicationSearchType": "1",
                "GD_Name": "",
                "CityID": "",
                "CountryID": "",
                "FromDate": "%s/%d" % (range_start, year_start),
                "ToDate": "%s/%d" % (range_end, year_end),
                "FromSum": "",
                "ToSum": "",
                "ID": None,
                "State": 0,
                "URL": None,
                "IsControl": False,
                "IsUpdate": False}

        resp = []
        for retries in range(10):
            try:
                resp = self.requests_post('https://statements.mevaker.gov.il/Handler/GuarantyDonationPublisherHandler.ashx',
                                          data={'action': 'gds',
                                                'd': json.dumps(data)})
                break
            except requests.exceptions.RequestException as e:
                logging.error('Retrying in a bit (%r)', e)
                time.sleep(1)

        assert len(resp) == 6
        if len(resp[0]) < 1000:
            return resp[0]
        else:
            logging.error('got %d results!', len(resp[0]))


    def get_for_candidate(self, cid):
        year_start = 2010
        year_end = datetime.datetime.now().year
        for year in range(year_start, year_end + 1):
            div = 1
            ret = []
            while div < 512 and len(ret) == 0:
                for range_start, range_end in ranges(div):
                    resp = self.get_for_range(cid, year, range_start, year, range_end)
                    if resp is None:
                        div *= 2
                        ret = []
                        break
                    ret.append(resp)
                break
            yield from ret

    def get_transactions(self, rows):
        for row in rows:
            cid = str(row['ID'])
            for resp in self.get_for_candidate(cid):
                for rr in resp:
                    rr["Party"] = row["Party"]
                    yield rr


def process_resources(res_iter_):
    first = next(res_iter_)
    yield GetTransactions().get_transactions(first)

def get_resource_descriptor():
    return {
        'name': 'transactions',
        PROP_STREAMING: True,
        'path': 'data/candidates.csv',
        'schema': {
            'fields': [
                {'name': 'CandidateName', 'type': 'string'},
                {'name': 'City', 'type': 'string'},
                {'name': 'Country', 'type': 'string'},
                {'name': 'GD_Date', 'type': 'string'},
                {'name': 'GD_Name', 'type': 'string'},
                {'name': 'GD_Sum', 'type': 'string'},
                {'name': 'GuaranteeOrDonation', 'type': 'string'},
                {'name': 'ID', 'type': 'integer'},
                {'name': 'IsControl', 'type': 'boolean'},
                {'name': 'IsUpdate', 'type': 'boolean'},
                {'name': 'Party', 'type': 'string'},
                {'name': 'PublisherTypeID', 'type': 'integer'},
                {'name': 'State', 'type': 'integer'},
                {'name': 'SumInCurrency', 'type': 'string'},
                {'name': 'URL', 'type': 'string'},
            ]
        }
    }


if __name__ == "__main__":
    params, dp, res_iter = ingest()
    dp['resources'][0] = get_resource_descriptor()
    spew(dp, process_resources(res_iter))
