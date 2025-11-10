Dockerfile -> Here you specify the base image aka the programming language/languages that you will use in your application
You also install all the required modules/libraries you will need like pandas or sqlalchemy. You specify the work directory of your containers in docker. In our case is WORKDIR /app. And lastly you run your main application app.py in our case with "CMD ["python", "app.py"]".

docker-compose.yml
Here we specify all the containers we want to run in docker. First we have the database container named db. We specify its a postgres and we use a postgres image. We also define username, password and database name. We also specify the port that it listens to which is 5432. And then we specify the volumes for this container. One of the volumes is the init.sql file which runs first when the container gets activated/started/up however you want to call it. Then all the data get saved on the second volume which is - db_data:/var/lib/postgresql.

Next we have the pasta system container which is basically linked to our python application app.py.

And last we got the pgAdmin container which we can use to connect to our database using the dbname, port, username and password. 

The pgAdmin listens to a port we define 5000 and we also define a pgAdmin email (admin@admin.com) and password to connect.

init.sql
Its a file that helps us to create the database tables and possibly insert some values before the app.py takes over. I feel like it simplifies the whole process even though its not needed and we could just initialize everything in the main application.



app.py
Its the main application in which we first create our connection with the database. Because the database does not connect immediately when we run the containers we have to make a while loop retry logic:
```python
while True:
    try:
        db_engine = get_db_engine()  # Create the engine
        LOGGER.info("Connected successfully")
        break
    except Exception as e:
        LOGGER.warning(f"Retrying connection to the database because of the issue {str(e)}")
        time.sleep(5)  # Wait before retrying

```
After that we create the first task which is to insert batches(in our database). It is an endless loop that after each iteration it waits 5 seconds until the next one. We define the insert query first:
```python
insert_query = text("""
    INSERT INTO pasta_db.batches (id, blade_type, isFresh, productionDate,inStock ) 
    VALUES (:id, :blade_type, :isFresh, NOW(), :inStock)
    """)
```
Then we define the new Stock amount that will get inserted which will be 10, the new random blade type which can be either A or B, the random Boolean value for isFresh and the id which gets incremented in every iteration. The production date is of course the current timestamp which we can get by just calling the sql method NOW().

```python
while True:
        new_inStock = 10  
        new_isFresh = random.choice([True, False])  # Randomly choose between True (fresh) and False (dry)
        new_blade_type = random.choice(['A', 'B'])  # Randomly choose between blade types A and B

        # Assign the current ID
        i += 1  # Increment for the next batch ID
        batch_id = i
        
        try:
            # Use a context manager for transaction handling and execute the query
            with db_engine.connect() as connection:  # Get a connection
                # Begin a transaction
                with connection.begin():  # This begins a new transaction
                    # Execute the insert query with parameters
                    connection.execute(insert_query, {
                        'id': batch_id,
                        'isFresh': new_isFresh,
                        'blade_type': new_blade_type,
                        'inStock': new_inStock
                    })
                    LOGGER.info(f"Inserted batch with id {batch_id}: inStock={new_inStock}, isFresh={new_isFresh}, blade_type={new_blade_type}")
```
After we insert the batch we check the storage levels if they are empty 