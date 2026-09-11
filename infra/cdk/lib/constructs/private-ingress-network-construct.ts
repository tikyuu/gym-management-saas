import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface PrivateIngressNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class PrivateIngressNetworkConstruct extends Construct {
  constructor(
    scope: Construct,
    id: string,
    props: PrivateIngressNetworkConstructProps,
  ) {
    super(scope, id);
  }
}
