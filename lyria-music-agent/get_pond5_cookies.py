import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    os.makedirs("data", exist_ok=True)
    print("🚀 Levantando navegador visible...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("🌐 Yendo a Pond5... Por favor INGRESÁ TU USUARIO Y CONTRASEÑA y resuelve cualquier Captcha.")
        await page.goto("https://www.pond5.com/member/login.do")
        
        # Le damos 2 minutos completos para que el usuario navegue y se loguee tranquilo
        print("⏳ Tienes 120 segundos para iniciar sesión. Mantén la ventana abierta hasta que este script termine.")
        await page.wait_for_timeout(120000)
        
        await context.storage_state(path="data/pond5_cookies.json")
        print("✅ ¡Éxito! Tu pasaporte fue robado y guardado en data/pond5_cookies.json")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
