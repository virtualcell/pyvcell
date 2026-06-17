"""The reader should parse best-effort: unmodeled / malformed physiology elements
are skipped instead of aborting the whole biomodel, so a SimulationSpec's
MathDescription and Geometry still load.

These minimal documents reproduce the three constructs that previously aborted
~23% of real public biomodels:
  - a stray ``<Parameter>`` outside the modeled containers ("Unexpected parent tag")
  - a ``<Kinetics>`` reached with a non-Reaction node ('"Model" object has no field "kinetics"')
  - a ``<Simulation>`` missing its solver/timebound children ("missing required child elements")
"""

import pyvcell.vcml as vc

# A BioModel whose physiology contains all three previously-fatal constructs,
# alongside a SimulationSpec that carries a real Geometry and MathDescription.
LENIENT_VCML = """<?xml version="1.0" encoding="UTF-8"?>
<vcml xmlns="http://sourceforge.net/projects/vcell/vcml" Version="test">
  <BioModel Name="LenientTest">
    <Model Name="m">
      <ModelParameters>
        <Parameter Name="k" Role="user defined" Unit="s-1">1.0</Parameter>
      </ModelParameters>
      <Feature Name="cell"/>
      <UnmodeledReactionContainer>
        <Kinetics KineticsType="GeneralKinetics">
          <Parameter Name="kStray" Role="user defined" Unit="x">2.0</Parameter>
        </Kinetics>
      </UnmodeledReactionContainer>
      <RateRule>
        <Parameter Name="pStray" Role="user defined" Unit="u">3.0</Parameter>
      </RateRule>
    </Model>
    <SimulationSpec Name="app" Stochastic="false">
      <Geometry Name="geo" Dimension="3">
        <Extent X="1.0" Y="1.0" Z="1.0"/>
        <Origin X="0.0" Y="0.0" Z="0.0"/>
        <SubVolume Name="subdomain0" Handle="0" Type="Analytical">
          <AnalyticExpression>1.0</AnalyticExpression>
        </SubVolume>
      </Geometry>
      <MathDescription Name="app_generated">
        <Constant Name="kConst">1.0</Constant>
        <VolumeVariable Name="u" Domain="subdomain0"/>
        <CompartmentSubDomain Name="subdomain0">
          <BoundaryType Boundary="Xm" Type="Value"/>
          <OdeEquation Name="u">
            <Rate>0.0</Rate>
            <Initial>kConst</Initial>
          </OdeEquation>
        </CompartmentSubDomain>
      </MathDescription>
      <Simulation Name="incomplete">
        <MeshSpecification>
          <Size X="10" Y="10" Z="10"/>
        </MeshSpecification>
      </Simulation>
    </SimulationSpec>
  </BioModel>
</vcml>
"""


def test_lenient_parse_preserves_math_and_geometry() -> None:
    biomodel = vc.VcmlReader.biomodel_from_str(LENIENT_VCML)

    # The document loads despite the stray Parameter / Kinetics and childless Simulation.
    assert biomodel is not None
    assert biomodel.name == "LenientTest"

    # Faithful physiology that IS modeled is still parsed.
    assert biomodel.model is not None
    assert [c.name for c in biomodel.model.compartments] == ["cell"]
    assert [p.name for p in biomodel.model.model_parameters] == ["k"]

    app = biomodel.applications[0]

    # Geometry survives intact.
    assert app.geometry.name == "geo"
    assert app.geometry.subvolume_names == ["subdomain0"]

    # MathDescription survives intact.
    assert app.math_description is not None
    assert [const.name for const in app.math_description.constants] == ["kConst"]
    subdomain = app.math_description.compartment_subdomains[0]
    assert [ode.name for ode in subdomain.ode_equations] == ["u"]

    # The incomplete Simulation is skipped (not fatal), the rest is preserved.
    assert app.simulations == []


def test_stray_kinetics_does_not_abort() -> None:
    """A <Kinetics> under a non-reaction container is skipped, not fatal."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<vcml xmlns="http://sourceforge.net/projects/vcell/vcml" Version="test">
  <BioModel Name="StrayKinetics">
    <Model Name="m">
      <Feature Name="cell"/>
      <SomeContainer>
        <Kinetics KineticsType="GeneralKinetics"/>
      </SomeContainer>
    </Model>
  </BioModel>
</vcml>
"""
    biomodel = vc.VcmlReader.biomodel_from_str(xml)
    assert biomodel.model is not None
    assert [c.name for c in biomodel.model.compartments] == ["cell"]
