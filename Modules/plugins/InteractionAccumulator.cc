#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

namespace dune {
  class InteractionAccumulator : public edm::global::EDProducer<> {
  public:
    explicit InteractionAccumulator(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

  private:
    std::vector<edm::EDGetTokenT<int>> getTokens_;
    const edm::EDPutTokenT<std::vector<int>> putToken_;

  };

  InteractionAccumulator::InteractionAccumulator(edm::ParameterSet const& iPSet):
    putToken_(produces<std::vector<int>>())
  {
    for(auto const& tag: iPSet.getParameter<std::vector<edm::InputTag>>("interactions")) {
      getTokens_.emplace_back(consumes<int>(tag));
    }
  }

  void InteractionAccumulator::produce(edm::StreamID,edm::Event& iEvent, edm::EventSetup const&) const 
  {
    for(auto const& token: getTokens_) {
      (void) iEvent.get(token);
    }
    iEvent.emplace(putToken_, 5);
  }
}

DEFINE_FWK_MODULE(dune::InteractionAccumulator);
