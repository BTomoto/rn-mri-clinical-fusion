"""Audit the officially published Aspera public links; never stores tokens or fits models.

By default reads the saved receipt. --refresh repeats bounded public-link metadata requests.
No whole-cohort download is initiated. Uses the public application's documented download flow.
"""
from pathlib import Path
import argparse
import base64
import datetime as dt
import hashlib
from html.parser import HTMLParser
import http.cookiejar
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/ucsd_feature_audit/mri_access_receipt.json'
PAGE='https://www.cancerimagingarchive.net/collection/ucsd-ptgbm/'
HOST='https://faspex.cancerimagingarchive.net'
TIMEOUT=20


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        h=dict(attrs).get('href','')
        if tag=='a' and 'faspex.cancerimagingarchive.net' in h and h not in self.links:
            self.links.append(h)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def request(url,body=None,headers=None,opener=None):
    h={'User-Agent':'RNPublicDataAudit/1.0'};h.update(headers or {})
    if body is not None:h['Content-Type']='application/json'
    req=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers=h)
    r=(opener.open(req,timeout=TIMEOUT) if opener else urllib.request.urlopen(req,timeout=TIMEOUT))
    return r,r.read()


def public_token(context,client,redirect,trace):
    """Mirror the public web client's authorize_public_link redirect, no user credentials."""
    state=base64.b64encode(json.dumps(context,separators=(',',':')).encode()).decode()
    params=dict(response_type='code',client_id=client,redirect_uri=redirect,state=state)
    opener=urllib.request.build_opener(NoRedirect,urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    url=HOST+'/aspera/faspex/auth/authorize_public_link?'+urllib.parse.urlencode(params)
    try:
        request(url,opener=opener)
        raise RuntimeError('Authorization requires interactive response')
    except urllib.error.HTTPError as exc:
        if exc.code!=302:raise
        q=urllib.parse.parse_qs(urllib.parse.urlsplit(exc.headers['Location']).query)
        if q.get('state')!=[state] or not q.get('code'):
            raise RuntimeError('Authorization requires additional interaction')
    r,b=request(HOST+'/aspera/faspex/auth/token',dict(client_id=client,redirect_uri=redirect,
        code=q['code'][0],state=state,grant_type='authorization_code'),opener=opener)
    trace['public_link_authorization_http_status']=r.status
    token=json.loads(b)['access_token']
    return token


def refresh():
    r,page=request(PAGE)
    p=Links();p.feed(page.decode(errors='replace'))
    _,config=request(HOST+'/aspera/faspex/config.js')
    cfg=config.decode();client=re.search(r"client_id:\s*'([^']+)'",cfg).group(1)
    redirect=HOST+re.search(r"redirect_uri:\s*'([^']+)'",cfg).group(1)
    receipt=dict(date='2026-10-29',checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        collection_url=PAGE,collection_http_status=r.status,collection_page_sha256=hashlib.sha256(page).hexdigest(),
        public_config_sha256=hashlib.sha256(config).hexdigest(),api_reference=HOST+'/aspera/faspex/api',
        authorization_method='official_public_link_web_flow; no user account credentials',
        clinical_workbook_current_sha256=None,packages=[],http_gateway_url=None,
        local_ascp_available=shutil.which('ascp') is not None,source_files_downloaded=0,
        pixel_quality_review_complete=False,case_level_MRI_join_verified=False,ROI_empirically_verified=False)
    # Check current source without replacing the pinned workbook.
    u='https://www.cancerimagingarchive.net/wp-content/uploads/UCSD_PTGBM-clinical-information_v3_2026-12-Mar.xlsx'
    _,b=request(u);receipt['clinical_workbook_current_sha256']=hashlib.sha256(b).hexdigest()
    for link in p.links:
        c=json.loads(base64.b64decode(urllib.parse.parse_qs(urllib.parse.urlsplit(link).query)['context'][0]))
        pid=c['package_id'];item=dict(package_id=pid,source='public link on collection page',probes=[])
        receipt['packages'].append(item)
        try:
            token=public_token(c,client,redirect,item)
        except Exception as e:
            item['authorization_error']=type(e).__name__;continue
        headers={'Authorization':'Bearer '+token}
        if receipt['http_gateway_url'] is None:
            try:
                _,b=request(HOST+'/aspera/faspex/api/v5/configuration',headers=headers)
                j=json.loads(b);receipt['http_gateway_url']=j.get('http_gateway_url')
                receipt['configuration_request_success']=True
            except Exception as e:receipt['configuration_request_error']=type(e).__name__
        endpoints=[('package_details','GET',f'/packages/{pid}?type=received',None),
                   ('file_listing','POST',f'/packages/{pid}/files/received?limit=20',{'path':'/','sort':'path'}),
                   ('connect_download_parameters','POST',f'/packages/{pid}/transfer_spec/download?type=received&transfer_type=connect',{}),
                   ('http_gateway_download_parameters','POST',f'/packages/{pid}/transfer_spec/download?type=received&transfer_type=http_gateway',
                    {'paths':[{'path':'/','basename':'UCSD-PTGBM','type':'directory','size':0}]})]
        for name,method,path,body in endpoints:
            started=time.monotonic();rec=dict(probe=name,method=method,path=path)
            try:
                r,b=request(HOST+'/aspera/faspex/api/v5'+path,body,headers);j=json.loads(b)
                rec.update(http_status=r.status,success=True,response_bytes=len(b))
                if name=='package_details':
                    rec['metadata']={k:j.get(k) for k in ['id','title','total_files','message','files_on_server','prevent_http_download']}
                    # API total_bytes metadata is inconsistent with the collection GB sizes, not used as verified size.
                    rec['api_reported_total_bytes']=j.get('total_bytes')
                elif name=='file_listing':
                    rec['items']=[{k:x.get(k) for k in ['path','basename','type','size']} for x in j.get('items',[])]
                    rec['total_count']=j.get('total_count')
                else:
                    rec['transfer_configuration']={k:j.get(k) for k in ['remote_host','remote_user','ssh_port','fasp_port','source_root','paths','zip_required'] if k in j}
                    rec['sensitive_transfer_tokens_omitted']=True
            except urllib.error.HTTPError as e:rec.update(success=False,http_status=e.code,error='HTTPError')
            except Exception as e:rec.update(success=False,error=type(e).__name__)
            rec['elapsed_seconds']=round(time.monotonic()-started,2);item['probes'].append(rec)
            print(pid,name,'ok' if rec['success'] else rec.get('error'),flush=True)
    receipt['conclusion']='Public metadata and transfer parameters accessible. Some file listings may time out; see each probe and the supplemental inventory receipt. No NIfTI downloaded or pixel/ROI quality verified. No HTTP gateway was configured at the time of this audit.'
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(receipt,indent=2))
    return receipt


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--refresh',action='store_true');args=a.parse_args()
    d=refresh() if args.refresh else json.loads(OUT.read_text())
    print(json.dumps({k:d[k] for k in ['source_files_downloaded','pixel_quality_review_complete','case_level_MRI_join_verified','conclusion']},indent=2))
