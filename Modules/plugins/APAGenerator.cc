#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"

namespace dune {

  class APAGenerator : public edm::global::EDProducer<> {
  public:
    explicit APAGenerator(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

  private:
    const size_t dataSize_;
    const edm::EDPutTokenT<std::vector<char>> token_;
  };


  APAGenerator::APAGenerator(edm::ParameterSet const& iPSet):
    dataSize_(iPSet.getParameter<unsigned int>("dataSize")),
    token_(produces<std::vector<char>>())
  {}

  void APAGenerator::produce(edm::StreamID,edm::Event& iEvent, edm::EventSetup const&) const
  {
    iEvent.emplace(token_, dataSize_,char(1));
  }
}

DEFINE_FWK_MODULE(dune::APAGenerator);
