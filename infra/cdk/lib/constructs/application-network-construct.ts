import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface ApplicationNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
  natGatewayId: string;
}

export class ApplicationNetworkConstruct extends Construct {
  constructor(
    scope: Construct,
    id: string,
    props: ApplicationNetworkConstructProps,
  ) {
    super(scope, id);
  }
}
