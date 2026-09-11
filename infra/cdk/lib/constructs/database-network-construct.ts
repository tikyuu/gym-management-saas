import { Construct } from "constructs";
import type { SubnetConfig } from "../types/subnet-config";

interface DatabaseNetworkConstructProps {
  vpcId: string;
  resourceNamePrefix: string;
  subnets: SubnetConfig[];
}

export class DatabaseNetworkConstruct extends Construct {
  constructor(
    scope: Construct,
    id: string,
    props: DatabaseNetworkConstructProps,
  ) {
    super(scope, id);
  }
}
