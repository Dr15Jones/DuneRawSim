#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

namespace dune {
  class InteractionFinder : public edm::global::EDProducer<> {
  public:
    explicit InteractionFinder(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

  private:
    std::vector<edm::EDGetTokenT<std::vector<float>>> clusterTokens_;
    const edm::EDPutTokenT<int> putToken_;
  };

  InteractionFinder::InteractionFinder(edm::ParameterSet const& iPSet):
    putToken_(produces<int>())
  {
    for(auto const& tag: iPSet.getParameter<std::vector<edm::InputTag>>("apaClusters")) {
      clusterTokens_.emplace_back(consumes<std::vector<float>>(tag));
    }
  }

  void InteractionFinder::produce(edm::StreamID,edm::Event& iEvent, edm::EventSetup const&) const 
  {
    for(auto const& token: clusterTokens_) {
      (void) iEvent.get(token);
    }

    iEvent.emplace(putToken_, 5);
  }
}

DEFINE_FWK_MODULE(dune::InteractionFinder);
