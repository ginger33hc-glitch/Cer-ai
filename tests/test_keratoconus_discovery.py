import os
os.environ.setdefault('OPENAI_API_KEY','test-key-for-import-only')
import pytest
from fastapi.testclient import TestClient
import canonical_engine

@pytest.mark.parametrize('path,alternate,language',[('/keratoconus-screening','/tr/keratokonus-tarama','en'),('/tr/keratokonus-tarama','/keratoconus-screening','tr')])
def test_screening_public_discovery(path,alternate,language):
    with TestClient(canonical_engine.app,base_url='https://cer-ai.com') as client:
        response=client.get(path)
        assert response.status_code==200
        assert response.headers['x-robots-tag'].startswith('index,follow')
        assert f'href="https://cer-ai.com{path}"' in response.text
        assert f'href="https://cer-ai.com{alternate}"' in response.text
        assert f'<html lang="{language}">' in response.text
        assert 'MedicalWebPage' in response.text
        assert 'href="/keratoconus"' in response.text
        assert f'<loc>https://cer-ai.com{path}</loc>' in client.get('/sitemap.xml').text
        assert 'type="file"' not in response.text
        if language == 'tr':
            assert '<h1>Keratokonus tarama testi</h1>' in response.text
            assert 'https://doi.org/10.4274/tjo.galenos.2023.68188' in response.text
            assert 'Bu çalışma CER-AI' in response.text
            assert '/tr/keratokonus-tarama' in client.get('/tr/learning-center').text

    with TestClient(canonical_engine.app,base_url='https://preview.example') as client:
        assert client.get(path).headers['x-robots-tag']=='noindex,nofollow'
