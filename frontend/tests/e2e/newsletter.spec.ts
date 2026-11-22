import {readdir,readFile} from 'node:fs/promises'
import {join} from 'node:path'
import {test,expect} from '@playwright/test'

const mailbox=process.env.ELVAA_E2E_MAIL_DIR

// Requires the loopback-only test SMTP sink and a disposable database.
test('newsletter requires a deliberate email confirmation and supports unsubscribe',async({page})=>{
 test.skip(!mailbox,'Set ELVAA_E2E_MAIL_DIR and run the local SMTP test sink with a disposable database.')
 test.setTimeout(90_000)
 const email=`news${Date.now().toString(36)}${Math.random().toString(36).slice(2,6)}@example.test`
 async function mail(subject:string){
  let found=''
  await expect.poll(async()=>{
   const files=await readdir(mailbox!)
   for(const file of files.filter(f=>f.endsWith('.eml'))){
    const text=await readFile(join(mailbox!,file),'utf8')
    if(text.includes(`To: ${email}`)&&text.includes(`Subject: ${subject}`)){found=text;return true}
   }
   return false
  },{timeout:15_000,message:`Waiting for test email: ${subject}`}).toBeTruthy()
  return found
 }
 await page.goto('/')
 await page.locator('#newsletter-email').fill(email)
 await page.getByRole('button',{name:'Subscribe to newsletter'}).click()
 await expect(page.getByText('If eligible, please check your inbox for a confirmation link.')).toBeVisible()
 const confirmation=await mail('Confirm your ELVAA newsletter subscription')
 const confirmUrl=confirmation.match(/https?:\/\/[^\s]+\/newsletter\/confirm#token=[^\s]+/)?.[0]
 expect(confirmUrl).toBeTruthy()
 await page.goto(confirmUrl!)
 await expect(page.getByRole('heading',{name:'Confirm your subscription.'})).toBeVisible()
 await page.getByRole('button',{name:'CONFIRM SUBSCRIPTION'}).click()
 await expect(page.getByText('Your newsletter subscription is confirmed.')).toBeVisible()
 expect(new URL(page.url()).hash).toBe('')
 const welcome=await mail('You are subscribed to ELVAA')
 const unsubscribeUrl=welcome.match(/https?:\/\/[^\s]+\/newsletter\/unsubscribe#token=[^\s]+/)?.[0]
 expect(unsubscribeUrl).toBeTruthy()
 await page.goto(unsubscribeUrl!)
 await page.getByRole('button',{name:'UNSUBSCRIBE',exact:true}).click()
 await expect(page.getByText('You have been unsubscribed from the ELVAA newsletter.')).toBeVisible()
 await page.goto(confirmUrl!)
 await page.getByRole('button',{name:'CONFIRM SUBSCRIPTION'}).click()
 await expect(page.locator('.form-error[role="alert"]')).toContainText('invalid or has expired')
})
