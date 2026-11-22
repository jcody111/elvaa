import {test,expect} from '@playwright/test'

test('homepage loads live products and search works',async({page})=>{
 await page.goto('/');await expect(page.getByRole('heading',{name:'A quieter kind of beautiful.'})).toBeVisible();await expect(page.locator('.product-card').first()).toBeVisible()
 await page.getByRole('button',{name:'Open search'}).click();await page.getByLabel('Search products').fill('blazer');await page.getByRole('button',{name:'SEARCH',exact:true}).click();await expect(page.getByRole('heading',{name:'Search results for “blazer”'})).toBeVisible();await expect(page.getByRole('link',{name:'The Studio Blazer'})).toBeVisible()
})
test('product options, bag and server-side coupon quote',async({page})=>{
 await page.goto('/product/the-studio-blazer');await page.getByRole('button',{name:'ADD TO BAG'}).click();await expect(page.locator('.buy-box [role=alert]')).toContainText('Please select a size')
 await page.getByRole('button',{name:'M',exact:true}).click();await page.getByRole('button',{name:'ADD TO BAG'}).click();await expect(page.getByText('Added to your bag')).toBeVisible()
 await page.goto('/cart');await page.locator('#coupon').fill('WELCOME10');await page.getByRole('button',{name:'APPLY'}).click();await expect(page.getByText('Discount',{exact:true})).toBeVisible();await expect(page.locator('.summary-total')).toContainText('170.10')
})
test('guest wishlist persists across reloads',async({page})=>{
 await page.goto('/product/the-everyday-tote');await page.getByRole('button',{name:'Add to wishlist'}).first().click();await page.goto('/wishlist');await expect(page.getByRole('link',{name:'The Everyday Tote'})).toBeVisible();await page.reload();await expect(page.getByRole('link',{name:'The Everyday Tote'})).toBeVisible()
})
test('mobile menu and catalog do not overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');await page.getByRole('button',{name:'Open menu'}).click();await expect(page.getByRole('navigation',{name:'Mobile navigation'})).toBeVisible();await page.getByRole('navigation',{name:'Mobile navigation'}).getByRole('link',{name:'Clothing'}).click();await expect(page.getByRole('heading',{name:'Clothing'})).toBeVisible();await page.getByRole('button',{name:'FILTERS'}).click();await expect(page.getByText('REFINE BY')).toBeVisible();expect(await page.evaluate(()=>document.body.scrollWidth<=window.innerWidth)).toBeTruthy()
})
