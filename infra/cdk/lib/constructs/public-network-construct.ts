import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface PublicNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class PublicNetworkConstruct extends Construct {
  constructor(scope: Construct, id: string, props: PublicNetworkConstructProps) {
    super(scope, id);
  }
}
