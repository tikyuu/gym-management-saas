import { Stack, StackProps, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";

interface NetworkStackProps extends StackProps {
  availabilityZones: string[];
  vpcCidr: string;
}

export class NetworkStack extends Stack {
  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    new ec2.Vpc(this, "Vpc", {
      availabilityZones: props.availabilityZones,
      ipAddresses: ec2.IpAddresses.cidr(props.vpcCidr),
      natGateways: 0,
      subnetConfiguration: [],
    });
  }
}
