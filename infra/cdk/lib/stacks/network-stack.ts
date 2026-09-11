import { Stack, StackProps, Tags, aws_ec2 as ec2 } from "aws-cdk-lib";
import { Construct } from "constructs";
import { ApplicationNetworkConstruct } from "../constructs/application-network-construct";
import { PrivateIngressNetworkConstruct } from "../constructs/private-ingress-network-construct";
import { PublicNetworkConstruct } from "../constructs/public-network-construct";
import type { SubnetConfig } from "../types/subnet-config";

interface NetworkStackProps extends StackProps {
  applicationName: string;
  environmentName: string;
  vpcCidr: string;
  publicSubnets: SubnetConfig[];
  privateIngressSubnets: SubnetConfig[];
  applicationSubnets: SubnetConfig[];
  databaseSubnets: SubnetConfig[];
}

export class NetworkStack extends Stack {
  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    const resourceNamePrefix = `${props.applicationName}-${props.environmentName}`;

    Tags.of(this).add("application", props.applicationName);
    Tags.of(this).add("environment", props.environmentName);
    Tags.of(this).add("managed-by", "aws-cdk");
    Tags.of(this).add("component", "network");

    const vpc = new ec2.Vpc(this, "Vpc", {
      ipAddresses: ec2.IpAddresses.cidr(props.vpcCidr),
      natGateways: 0,
      subnetConfiguration: [],
      vpcName: `${resourceNamePrefix}-vpc`,
    });

    const publicNetwork = new PublicNetworkConstruct(this, "PublicNetwork", {
      vpcId: vpc.vpcId,
      resourceNamePrefix,
      subnets: props.publicSubnets,
    });

    const privateIngressNetwork = new PrivateIngressNetworkConstruct(
      this,
      "PrivateIngressNetwork",
      {
        vpcId: vpc.vpcId,
        resourceNamePrefix,
        subnets: props.privateIngressSubnets,
      },
    );

    const applicationNetwork = new ApplicationNetworkConstruct(
      this,
      "ApplicationNetwork",
      {
        vpcId: vpc.vpcId,
        resourceNamePrefix,
        subnets: props.applicationSubnets,
        natGatewayId: publicNetwork.natGateway.ref,
      },
    );

    props.applicationSubnets.forEach((subnet) => {
      const applicationSubnet = new ec2.CfnSubnet(this, subnet.id, {
        availabilityZone: subnet.availabilityZone,
        cidrBlock: subnet.cidrBlock,
        mapPublicIpOnLaunch: false,
        tags: [
          {
            key: "Name",
            value: `${resourceNamePrefix}-${subnet.name}`,
          },
        ],
        vpcId: vpc.vpcId,
      });

      new ec2.CfnSubnetRouteTableAssociation(
        this,
        `${subnet.id}RouteTableAssociation`,
        {
          routeTableId: applicationNetwork.routeTable.ref,
          subnetId: applicationSubnet.ref,
        },
      );
    });

    const databaseRouteTable = new ec2.CfnRouteTable(
      this,
      "DatabaseRouteTable",
      {
        tags: [
          {
            key: "Name",
            value: `${resourceNamePrefix}-private-database-rt`,
          },
        ],
        vpcId: vpc.vpcId,
      },
    );

    props.databaseSubnets.forEach((subnet) => {
      const databaseSubnet = new ec2.CfnSubnet(this, subnet.id, {
        availabilityZone: subnet.availabilityZone,
        cidrBlock: subnet.cidrBlock,
        mapPublicIpOnLaunch: false,
        tags: [
          {
            key: "Name",
            value: `${resourceNamePrefix}-${subnet.name}`,
          },
        ],
        vpcId: vpc.vpcId,
      });

      new ec2.CfnSubnetRouteTableAssociation(
        this,
        `${subnet.id}RouteTableAssociation`,
        {
          routeTableId: databaseRouteTable.ref,
          subnetId: databaseSubnet.ref,
        },
      );
    });
  }
}
