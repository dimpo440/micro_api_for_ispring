Micro service for registration on online education platform Ispring.


What was changed in fork:
Originally nothing worked from the box, that was only prototype, so:
- Simplified validation
- Setup nessesary fields
- Adapted for Ispring API documentation from https://www.ispringsolutions.com/docs/display/learn/REST+API
- Added password generation

Endpoint /api/register  
require POST request JSON  
{  
"name": "Иван",  
"surname": "Петров",  
"email": "email@email.com",  
"phone": "+78975678920"  
}
Outputs for request:
- 201 successfull creation of user, initial password included
- 422 validation/user exist error, with error text
- 500 other errors, with error message text

{
"message": "Internal Server Error"
}

