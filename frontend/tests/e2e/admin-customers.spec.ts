import {test,expect} from '@playwright/test'

const username=process.env.ELVAA_E2E_STAFF_USERNAME
const password=process.env.ELVAA_E2E_STAFF_PASSWORD

// Creates a customer account and audit entries. Use a disposable test database.
test('staff can inspect and safely deactivate a customer account',async({page})=>{
 test.skip(!username||!password,'Set ELVAA_E2E_STAFF_USERNAME and ELVAA_E2E_STAFF_PASSWORD for the isolated staff test.')
 test.setTimeout(60_000)
 await page.goto('/account')
 await page.locator('#username').fill(username!)
 await page.locator('#password').fill(password!)
 const login=page.waitForResponse(r=>r.url().includes('/api/v1/auth/login/')&&r.request().method()==='POST')
 await page.locator('form').getByRole('button',{name:'SIGN IN'}).click()
 expect((await login).status()).toBe(200)
 const name=`customer${Date.now().toString(36)}${Math.random().toString(36).slice(2,5)}`
 const email=`${name}@example.test`
 const created=await page.request.post('/api/v1/auth/register/',{data:{username:name,email,password:'CustomerForest!5729',first_name:'Test'}})
 expect(created.status(),await created.text()).toBe(201)
 await page.goto('/admin/customers')
 await page.getByLabel('Search customers').fill(email)
 const row=page.locator('tr',{hasText:email})
 await expect(row).toContainText('Active')
 await row.getByRole('button',{name:'VIEW ORDERS'}).click()
 await expect(page.getByText('No account-linked orders yet.')).toBeVisible()
 page.once('dialog',dialog=>dialog.accept())
 await row.getByRole('button',{name:'DEACTIVATE'}).click()
 await expect(row.getByText('Inactive',{exact:true})).toBeVisible()
 page.once('dialog',dialog=>dialog.accept())
 await row.getByRole('button',{name:'REACTIVATE'}).click()
 await expect(row.getByText('Active',{exact:true})).toBeVisible()
})
