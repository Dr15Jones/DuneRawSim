#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

namespace dune {
  class InteractionProcessor : public edm::global::EDProducer<> {
  public:
    explicit InteractionProcessor(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

  private:
    int milliSecSleep_;
    const edm::EDGetTokenT<std::vector<int>> getToken_;
    const edm::EDPutTokenT<std::vector<double>> putToken_;

  };

  InteractionProcessor::InteractionProcessor(edm::ParameterSet const& iPSet):
    milliSecSleep_(iPSet.getUntrackedParameter<int>("uSleep")),
    getToken_(consumes<std::vector<int>>(iPSet.getParameter<edm::InputTag>("interactions"))),
    putToken_(produces<std::vector<double>>())
  {
  }

  void InteractionProcessor::produce(edm::StreamID,edm::Event& iEvent, edm::EventSetup const&) const 
  {
    (void) iEvent.get(getToken_);

    std::this_thread::sleep_for(std::chrono::milliseconds(milliSecSleep_));

    iEvent.emplace(putToken_, 5);
  }
}

DEFINE_FWK_MODULE(dune::InteractionProcessor);
