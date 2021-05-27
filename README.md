# DuneRawSim

## Overview
This code is meant to simulate the memory needs for the DUNE experiment's data processing of RAW data. The data consists of readouts from 150 APAs with each APA needed 40MB of data. The 150 APA readouts consists of one 'trigger' Event. The simulation is broken down into the following processing steps applied to each Event.

1. Reading one APA's data *on demand*. This is handled by the `dune::APAGenerator` EDProducer. The job has one `dune::APAGenerator` per APA. Each `dune::APAGenerator` places a 40MB `std::vector<char>` into the Event.
1. Based on one APA's data, find all clusters in that APA. This is handled by the `dune::APAClusterer` EDProducer. The job has one `dune::APAClusterer` per APA. Each `dune::APAClusterer` places a 400kB `std::vector<float>` into the Event. In addition, each `dune::APAClusterer` sleeps for 0.1 seconds (to simulate the time it takes to find the clusters).
1. Based on the clusters from the two nearest neighboring APA, determine if the clusters crossed the APA boundaries. This is meant to find `neutrino interactions` within or across the APAs. This is handled by the `dune::InteractionFinder` EDProducer. The job has 148 `dune::InteartionFinder` which corresponds to one per nearest neighbor APA groupings.
1. Based on all potential `neutrino interactions` found, reduce down to just the best ones. This is handled by the `dune::InteractionAccumulator`.
1. From the interactions, finish the processing needed. THis is handled by the `dune::InteractionProcessor` EDProducer. This module sleeps for 20 seconds (to simulate the time it would take to process the interactions).

There is also a general purpose module, `dune::MemoryUseProd` which can be used to model all of the above modules. The module puts an `std::vector<char>` into the Event and reads 0 or more `std::vector<char>` from the Event. This allows one to create a network of interdependent `dune::MemoryUseProd`s. The module has the following parameters

* `dataSizes` : A list of the amount of memory (in bytes) to create each Event. The list item used for a given Event is determined by taking the modulo of the Event number. Default is `[0]`.
* `uSleeps`: A list of the amount of time to sleep (in microseconds) for each Event. The list item used for a given Event is determined by taking the modulo of the Event number. Defaults to `[0]`.
* `consume`: A list of `InputTag`s which define which data products from other modules should be consumed by the module. Default is `[]`.
* `mightGet`: This is a parameter added to all modules by the Framework. It is used in conjunction with the _delete early_ facility.

NOTE: one can see these options by doing `edmPluginHelp -p dune::MemoryUseProd`

## Building the Code

This code requires access the the CMSSW runtime. This can be accomplished from any machine that has CVMFS access by doing the following

1. `source /cvmfs/cms.cern.ch/cmsset_default.sh`
1. `scram project CMSSW_11_3_0`
1. `cd CMSSW_11_3_0`
1. `cmsenv`
1. `cd src`

Next, download the code from GitHub
* `git clone https://github.com/Dr15Jones/DuneRawSim.git`

Build the code (note change `6` to how ever many cores you want to use to build)
* `scram b -j 6`

## Running the job

From the `src` directory do
* `cmsRun DuneRawSim/dune_workflow_cfg.py`

One can change the configuration file to test different behaviors.
* see the effect of not deleting the APA data by commenting out line
   * `process.options.canDeleteEarly = deleteEarlyList`
* change the number of threads used by changing line
   * `nThreads = 1`
* make number of concurrent events be different from the number of threads by changing line
   * `process.options.numberOfStreams = nThreads`
` 
