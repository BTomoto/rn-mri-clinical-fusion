"""Get tables linked by the author's public download button; preserve old sources.

Only the published read-only download endpoint is called. No account is needed.
"""
from pathlib import Path
import hashlib
import json
import urllib.request
import io
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ENDPOINT='https://molab.es/wp-json/sy_datasets/v1/get_partes_fichero/metasrd_excel_clinical_data'
HEADERS={'User-Agent':'RNPublicDataAudit/1.0'}


def main():
    meta=ROOT/'data/metadata/endpoint_followup'
    raw=ROOT/'data/raw/openbtai_molab_current'
    meta.mkdir(parents=True,exist_ok=True);raw.mkdir(parents=True,exist_ok=True)
    response=urllib.request.urlopen(urllib.request.Request(ENDPOINT,headers=HEADERS),timeout=45).read()
    data=json.loads(response)
    if data.get('code')!='ok':raise ValueError('Public file listing failed')
    (meta/'molab_metasrd_excel_clinical_data.json').write_bytes(response)
    existing=meta/'molab_downloaded_sources.json'
    pinned={r['source_url']:r['sha256'] for r in json.loads(existing.read_text())} if existing.exists() else {}
    records=[]
    for item in data['data']['result']:
        url=item['url']
        if not url.startswith('https://dw.molab.es/indices/bm1/') or not url.endswith('.xlsx'):
            raise ValueError('Unexpected download URL; review the source listing')
        name=url.rsplit('/',1)[1]
        with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=60) as r:
            b=r.read();resolved=r.url;last=r.headers.get('Last-Modified')
        sha=hashlib.sha256(b).hexdigest()
        if url in pinned and pinned[url]!=sha:
            raise ValueError(f'Source changed: {name}; retain the old version and review before replacing it')
        (raw/name).write_bytes(b)
        records.append(dict(source_url=url,resolved_url=resolved,local_path=str((raw/name).relative_to(ROOT)),
            size_bytes=len(b),sha256=sha,md5=hashlib.md5(b).hexdigest(),last_modified=last,
            checked_date='2026-10-28',discovery_url=ENDPOINT,
            license_note='Source website requires the Scientific Data 2023 citation; no separate file-level license observed.'))
        print(name,len(b),sha)
    existing.write_text(json.dumps(records,indent=2))
    # The author's bulk package serves a differently named clinical snapshot.
    inventory=json.loads((meta/'molab_excel_archive_inventory.json').read_text())
    sept=raw/'OpenBTAI_METS_ClinicalData_Sept2023.xlsx'
    member=next(x for x in inventory['files'] if x['name']==sept.name)
    if not sept.exists():
        archive=urllib.request.urlopen(urllib.request.Request(inventory['url'],headers=HEADERS),timeout=60).read()
        if hashlib.sha256(archive).hexdigest()!=inventory['sha256']:
            raise ValueError('Bulk Excel archive changed; review the new version')
        with zipfile.ZipFile(io.BytesIO(archive)) as z:payload=z.read(member['name'])
        if hashlib.sha256(payload).hexdigest()!=member['sha256']:raise ValueError('Clinical member hash mismatch')
        sept.write_bytes(payload)
    elif hashlib.sha256(sept.read_bytes()).hexdigest()!=member['sha256']:
        raise ValueError('Local September clinical source differs from the pinned archive')


if __name__=='__main__':main()
