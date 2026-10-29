"""Bounded retry for two actual sample FLAIR files; no credentials/tokens are saved.

This retrieves transfer parameters and tests the advertised TCP connection. It does not
equate download parameters with downloaded images. Default reads the saved receipt.
"""
from pathlib import Path
import argparse,base64,datetime as dt,json,re,shutil,socket,time,urllib.parse
from audit_ucsd_mri_access import request,Links,public_token,PAGE,HOST
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/ucsd_clinical_revalidation/mri_sample_transfer_retry.json'


def refresh():
    r=dict(date='2026-10-29',checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
           purpose='Two selected FLAIR files only; not a whole-package transfer',
           source_NIfTI_files_downloaded=0,source_NIfTI_bytes_downloaded=0,
           pixel_QC_complete=False,symlink_targets_resolved=False,local_ascp_available=shutil.which('ascp') is not None)
    try:
        _,b=request(PAGE);p=Links();p.feed(b.decode(errors='replace'))
        contexts=[json.loads(base64.b64decode(urllib.parse.parse_qs(urllib.parse.urlsplit(x).query)['context'][0])) for x in p.links]
        ctx=next(x for x in contexts if x['package_id']=='1221')
        _,b=request(HOST+'/aspera/faspex/config.js');cfg=b.decode()
        client=re.search(r"client_id:\s*'([^']+)'",cfg).group(1)
        redirect=HOST+re.search(r"redirect_uri:\s*'([^']+)'",cfg).group(1)
        token=public_token(ctx,client,redirect,r);headers={'Authorization':'Bearer '+token}
        _,b=request(HOST+'/aspera/faspex/api/v5/configuration',headers=headers)
        r['http_gateway_url']=json.loads(b).get('http_gateway_url')
        paths=[dict(path=f'/UCSD-PTGBM-BraTS-2024-test-set/{i}/{i}_FLAIR.nii.gz',basename=f'{i}_FLAIR.nii.gz',type='file')
               for i in ['UCSD-PTGBM-0001_01','UCSD-PTGBM-0003_01']]
        r['requested_files']=[x['path'] for x in paths]
        response,b=request(HOST+'/aspera/faspex/api/v5/packages/1221/transfer_spec/download?type=received&transfer_type=connect',{'paths':paths},headers)
        spec=json.loads(b);r['download_parameter_http_status']=response.status
        r['transfer_parameter_paths']=[x.get('source') for x in spec.get('paths',[])]
        host,port=spec['remote_host'],int(spec['ssh_port']);start=time.monotonic()
        try:
            with socket.create_connection((host,port),timeout=4):network=dict(success=True,description='TCP connection only, not a FASP transfer')
        except OSError as e:network=dict(success=False,error=type(e).__name__,errno=e.errno,description='Advertised Aspera endpoint unreachable from this execution environment; cause not further adjudicated')
        r['advertised_endpoint_connection']=dict(host=host,port=port,elapsed_seconds=round(time.monotonic()-start,2),**network)
        r['actual_data_transfer_started']=False
        r['conclusion']='Specific-file transfer parameters obtained; actual transfer not started because this environment lacks the Aspera client / usable transfer route. No image bytes or symlink targets verified.'
    except Exception as e:
        r['request_error']=type(e).__name__;r['actual_data_transfer_started']=False
        r['conclusion']='Bounded public sample retrieval retry could not establish a data-transfer path. No images downloaded; see request_error.'
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(r,indent=2));return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--refresh',action='store_true');a=p.parse_args()
    r=refresh() if a.refresh else json.loads(OUT.read_text())
    print(json.dumps(r,indent=2))
