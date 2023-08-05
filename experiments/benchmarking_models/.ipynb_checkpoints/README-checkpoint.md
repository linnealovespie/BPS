# Models to Predict Emissions between 2027-2050 with BEPS

This repo models emissions from large (>20k sq ft) Seattle buildings between 2027 and 2050 for different benchmark proposals for BEPS.

The original model was built in Excel by RMI. This repo corrects some calculation errors in that model and also allows the user to model a new scenario by writing a single new function and then running the model. See below for instructions.

## Tests

To run tests, in the `benchmarking_models/` directory, run:
`$ python3 -m pytest`

To clear the cache:
`$ pytest --cache-clear`
